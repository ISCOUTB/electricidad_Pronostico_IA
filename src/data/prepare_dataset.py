"""Alinea los datos crudos y prepara variables t para el objetivo t+1."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import holidays
import numpy as np
import pandas as pd

from src.data.project_config import load_data_cutoff, load_project_config

LOGGER = logging.getLogger("prepare_dataset")
START_DATE = date(2015, 1, 1)
XM_METRICS = (
    "PPPrecBolsNaci",
    "DemaSIN",
    "AporEner",
    "AporEnerMediHist",
    "VoluUtilDiarEner",
)
WEATHER_POINTS = (
    "barranquilla",
    "bogota",
    "medellin",
    "cali",
    "guatape_el_penol",
    "guavio",
)
WEATHER_FIELDS = {
    "temperature_2m_mean": "temperature_mean",
    "temperature_2m_max": "temperature_max",
    "precipitation_sum": "precipitation",
}


def expected_dates(cutoff: date) -> pd.DatetimeIndex:
    """Genera el calendario diario que toda fuente cruda debe cubrir."""
    return pd.date_range(START_DATE, cutoff, freq="D", name="date")


def read_xm_metric(raw_root: Path, metric_id: str) -> pd.Series:
    """Lee Items/DailyEntities de una métrica sin alterar los crudos."""
    metric_dir = raw_root / "xm" / metric_id
    files = sorted(
        path
        for path in metric_dir.glob("*.json")
        if not path.name.endswith("_metadata.json")
    )
    if not files:
        raise FileNotFoundError(f"No hay respuestas crudas para XM {metric_id}.")

    observations: list[tuple[pd.Timestamp, float]] = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload.get("Items"), list):
            raise ValueError(f"{path} no contiene una lista Items.")
        for item in payload["Items"]:
            entities = item.get("DailyEntities")
            if not isinstance(entities, list):
                raise ValueError(f"{path}: falta DailyEntities para {item!r}.")
            matches = [
                entity
                for entity in entities
                if isinstance(entity, dict) and entity.get("Id") == "Sistema"
            ]
            if len(matches) != 1 or "Value" not in matches[0]:
                raise ValueError(
                    f"{path}: se esperaba un valor para Sistema en {item!r}."
                )
            value = matches[0]["Value"]
            if value is None:
                raise ValueError(f"{path}: valor nulo para {metric_id}.")
            try:
                numeric_value = float(value)
                day = pd.Timestamp(item["Date"])
            except (TypeError, ValueError, KeyError) as error:
                raise ValueError(f"Registro XM inválido en {path}: {item!r}") from error
            if not np.isfinite(numeric_value):
                raise ValueError(f"Valor no finito de {metric_id} en {day}.")
            observations.append((day, numeric_value))

    result = pd.Series(
        [value for _, value in observations],
        index=pd.DatetimeIndex([day for day, _ in observations], name="date"),
        name=metric_id,
        dtype="float64",
    ).sort_index()
    if result.index.has_duplicates:
        duplicated = result.index[result.index.duplicated()].unique()
        raise ValueError(f"Fechas duplicadas en {metric_id}: {duplicated[:5].tolist()}")
    return result


def read_openmeteo_point(raw_root: Path, point: str) -> pd.DataFrame:
    """Lee los tres campos diarios crudos de un punto Open-Meteo."""
    path = raw_root / "openmeteo" / point / "response.json"
    if not path.is_file():
        raise FileNotFoundError(f"No existe la respuesta Open-Meteo: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise ValueError(f"{path} no contiene daily.")
    if payload.get("timezone") != "America/Bogota":
        raise ValueError(
            f"{path}: zona {payload.get('timezone')!r}; se esperaba America/Bogota."
        )
    dates = daily.get("time")
    if not isinstance(dates, list):
        raise ValueError(f"{path}: falta la lista daily.time.")

    columns: dict[str, list[Any]] = {}
    for api_field in WEATHER_FIELDS:
        values = daily.get(api_field)
        if not isinstance(values, list) or len(values) != len(dates):
            raise ValueError(
                f"{path}: campo {api_field} no coincide en longitud con daily.time."
            )
        columns[f"climate_{point}_{api_field}"] = values

    frame = pd.DataFrame(
        columns,
        index=pd.DatetimeIndex(pd.to_datetime(dates), name="date"),
    )
    if frame.index.has_duplicates:
        raise ValueError(f"Fechas duplicadas en Open-Meteo {point}.")
    for column in frame:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


def validate_alignment(daily_wide: pd.DataFrame, cutoff: date) -> None:
    """Exige cobertura completa, sin huecos, duplicados ni nulos."""
    expected = expected_dates(cutoff)
    if not daily_wide.index.equals(expected):
        actual = daily_wide.index
        missing = expected.difference(actual)
        extra = actual.difference(expected)
        raise ValueError(
            "La alineación no cubre exactamente todas las fechas esperadas: "
            f"esperadas={len(expected)}, recibidas={len(actual)}, "
            f"faltantes={missing[:10].strftime('%Y-%m-%d').tolist()}, "
            f"extras={extra[:10].strftime('%Y-%m-%d').tolist()}."
        )
    nulls = daily_wide.isna().sum()
    if nulls.any():
        raise ValueError(
            "Hay nulos en los datos alineados: "
            f"{nulls[nulls > 0].to_dict()}."
        )


def load_daily_wide(raw_root: Path, cutoff: date) -> pd.DataFrame:
    """Alinea las cinco métricas XM y seis series climáticas por fecha."""
    series = [read_xm_metric(raw_root, metric_id) for metric_id in XM_METRICS]
    weather = [
        read_openmeteo_point(raw_root, point) for point in WEATHER_POINTS
    ]
    daily_wide = pd.concat([*series, *weather], axis=1).sort_index()
    validate_alignment(daily_wide, cutoff)
    return daily_wide


def _feature_groups(
    daily_wide: pd.DataFrame, config: dict[str, Any]
) -> dict[str, pd.DataFrame]:
    """Calcula únicamente predictores cuyo dato fuente está disponible hasta t."""
    groups: dict[str, pd.DataFrame] = {}
    price = daily_wide["PPPrecBolsNaci"]
    groups["price"] = pd.DataFrame(
        {
            "price_t": price,
            "price_lag_1": price.shift(1),
            "price_lag_2": price.shift(2),
            "price_lag_3": price.shift(3),
            "price_lag_6": price.shift(6),
            "price_mean_7d": price.rolling(7, min_periods=7).mean(),
            "price_mean_14d": price.rolling(14, min_periods=14).mean(),
            "price_mean_30d": price.rolling(30, min_periods=30).mean(),
            "price_std_7d": price.rolling(7, min_periods=7).std(),
            "price_std_30d": price.rolling(30, min_periods=30).std(),
            "price_max_30d": price.rolling(30, min_periods=30).max(),
        },
        index=daily_wide.index,
    )

    demand = daily_wide["DemaSIN"]
    groups["demand"] = pd.DataFrame(
        {
            "demand_t": demand,
            "demand_mean_7d": demand.rolling(7, min_periods=7).mean(),
        },
        index=daily_wide.index,
    )

    target_dates = daily_wide.index + pd.Timedelta(days=1)
    holidays_by_year = holidays.country_holidays(
        config["holidays"]["country"],
        years=range(target_dates[0].year, target_dates[-1].year + 1),
    )
    groups["calendar"] = pd.DataFrame(
        {
            "target_day_of_week": target_dates.dayofweek,
            "target_is_non_working": [
                day.dayofweek >= 5 or day.date() in holidays_by_year
                for day in target_dates
            ],
            "target_month": target_dates.month,
        },
        index=daily_wide.index,
    )

    aportes = daily_wide["AporEner"]
    aporte_mean = daily_wide["AporEnerMediHist"]
    ratio = aportes / aporte_mean
    volume = daily_wide["VoluUtilDiarEner"]
    groups["hydro"] = pd.DataFrame(
        {
            "aportes_t": aportes,
            "aportes_media_hist_t": aporte_mean,
            "aportes_ratio_t": ratio,
            "aportes_ratio_mean_7d": ratio.rolling(7, min_periods=7).mean(),
            "aportes_ratio_mean_30d": ratio.rolling(30, min_periods=30).mean(),
            "volumen_util_t": volume,
            "volumen_util_change_7d": volume - volume.shift(7),
        },
        index=daily_wide.index,
    )

    climate: dict[str, pd.Series] = {}
    for point in WEATHER_POINTS:
        mean_column = f"climate_{point}_temperature_2m_mean"
        max_column = f"climate_{point}_temperature_2m_max"
        precipitation_column = f"climate_{point}_precipitation_sum"
        precipitation = daily_wide[precipitation_column]
        climate[f"climate_{point}_temperature_mean_t"] = daily_wide[mean_column]
        climate[f"climate_{point}_temperature_max_t"] = daily_wide[max_column]
        climate[f"climate_{point}_precipitation_t"] = precipitation
        climate[f"climate_{point}_precipitation_sum_7d"] = precipitation.rolling(
            7, min_periods=7
        ).sum()
        climate[f"climate_{point}_precipitation_sum_30d"] = precipitation.rolling(
            30, min_periods=30
        ).sum()
    groups["climate"] = pd.DataFrame(climate, index=daily_wide.index)

    expected_groups = config["feature_groups"]
    for group_name, frame in groups.items():
        expected_columns = expected_groups[group_name]
        if frame.columns.tolist() != expected_columns:
            raise ValueError(
                f"Las columnas calculadas de {group_name} no coinciden con "
                f"config/config.yaml: {frame.columns.tolist()}."
            )
    return groups


def build_feature_frame(
    daily_wide: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    """Construye features t, calendario t+1 y etiqueta t+1."""
    groups = _feature_groups(daily_wide, config)
    features = pd.concat(list(groups.values()), axis=1)
    feature_columns = [
        column
        for group_columns in config["feature_groups"].values()
        for column in group_columns
    ]
    target_dates = daily_wide.index + pd.Timedelta(days=1)
    frame = features.copy()
    frame.insert(0, "date", daily_wide.index.strftime("%Y-%m-%d"))
    frame.insert(1, "target_date", target_dates.strftime("%Y-%m-%d"))
    frame["y_next"] = daily_wide["PPPrecBolsNaci"].shift(-1)
    frame = frame.dropna(subset=feature_columns)
    return frame


def add_auxiliary_columns(
    feature_frame: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Ajusta terciles solo con train y añade etiquetas auxiliares."""
    partitions = config["partitions"]
    dates = pd.to_datetime(feature_frame["target_date"])
    train_mask = dates.between(
        pd.Timestamp(partitions["train"]["start"]),
        pd.Timestamp(partitions["train"]["end"]),
        inclusive="both",
    )
    train_ratio = feature_frame.loc[train_mask, "aportes_ratio_t"]
    if train_ratio.empty:
        raise ValueError("No hay razones aportes/media para calcular cortes en train.")
    q1, q2 = train_ratio.quantile([1 / 3, 2 / 3]).tolist()
    if q1 > q2:
        raise ValueError(f"Cortes de terciles inválidos: {q1} > {q2}.")

    frame = feature_frame.copy()
    ratio = frame["aportes_ratio_t"]
    frame["hydro_regime"] = np.select(
        [ratio <= q1, ratio <= q2],
        ["bajo", "medio"],
        default="alto",
    )
    target_date = pd.to_datetime(frame["target_date"])
    frame["tipo_dia"] = np.where(
        frame["target_is_non_working"], "no_laboral", "habil"
    )
    frame["year"] = target_date.dt.year
    return frame, {"q1": float(q1), "q2": float(q2)}


def split_dataset(
    frame: pd.DataFrame, config: dict[str, Any]
) -> dict[str, pd.DataFrame]:
    """Parte por target_date y comprueba la cobertura esperada de cada corte."""
    target_dates = pd.to_datetime(frame["target_date"])
    partitions: dict[str, pd.DataFrame] = {}
    for name, bounds in config["partitions"].items():
        mask = target_dates.between(
            pd.Timestamp(bounds["start"]),
            pd.Timestamp(bounds["end"]),
            inclusive="both",
        )
        part = frame.loc[mask].copy()
        if len(part) != bounds["expected_rows"]:
            raise ValueError(
                f"Partición {name}: se esperaban {bounds['expected_rows']} filas, "
                f"se obtuvieron {len(part)}."
            )
        partitions[name] = part

    assigned = sum(len(part) for part in partitions.values())
    if assigned != len(frame):
        raise ValueError(
            f"Las particiones cubren {assigned} de {len(frame)} filas."
        )
    return partitions


def prepare_dataset(project_root: Path) -> dict[str, Any]:
    """Alinea entradas crudas, valida, construye predictores y exporta particiones."""
    config = load_project_config(project_root)
    cutoff = load_data_cutoff(project_root)
    raw_root = project_root / "data" / "raw"
    daily_wide = load_daily_wide(raw_root, cutoff)

    # No se escriben salidas hasta comprobar la cobertura cruda completa.
    interim_path = project_root / "data" / "interim" / "daily_wide.csv"
    interim_path.parent.mkdir(parents=True, exist_ok=True)
    daily_wide.to_csv(interim_path, index_label="date", date_format="%Y-%m-%d")

    feature_frame = build_feature_frame(daily_wide, config)
    labeled_frame = feature_frame.dropna(subset=["y_next"]).copy()
    initial_rows = len(daily_wide) - len(labeled_frame)
    labeled_frame, tercile_cutoffs = add_auxiliary_columns(labeled_frame, config)
    partitions = split_dataset(labeled_frame, config)

    processed_dir = project_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    for name, part in partitions.items():
        part.to_csv(
            processed_dir / f"{name}.csv",
            index=False,
            date_format="%Y-%m-%d",
        )

    feature_count = sum(len(columns) for columns in config["feature_groups"].values())
    return {
        "daily_wide_rows": len(daily_wide),
        "feature_rows": len(labeled_frame),
        "discarded_rows": initial_rows,
        "rows_by_partition": {
            name: len(part) for name, part in partitions.items()
        },
        "columns_by_group": {
            name: len(columns)
            for name, columns in config["feature_groups"].items()
        },
        "feature_count": feature_count,
        "auxiliary_columns": config["auxiliary_columns"],
        "tercile_cutoffs_train": tercile_cutoffs,
        "interim_path": str(interim_path),
        "processed_paths": {
            name: str(processed_dir / f"{name}.csv") for name in partitions
        },
    }


def main() -> None:
    """Ejecuta la preparación y muestra los conteos de filas y variables."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    root = Path(__file__).resolve().parents[2]
    summary = prepare_dataset(root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
