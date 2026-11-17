"""Descarga respuestas crudas de métricas diarias de XM por ventanas."""

from __future__ import annotations

import argparse
from collections import Counter
import importlib.metadata
import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from pydataxm.pydataxm import ReadDB

from src.data.project_config import load_data_cutoff

LOGGER = logging.getLogger("download_xm")
START_DATE = date(2015, 1, 1)
ENTITY = "Sistema"
WINDOW_DAYS = 30
PAUSE_SECONDS = 1.0
RETRY_DELAYS_SECONDS = (2, 4, 8)
RECENT_DAYS = 30
METRIC_IDS = (
    "PPPrecBolsNaci",
    "DemaSIN",
    "AporEner",
    "AporEnerMediHist",
    "VoluUtilDiarEner",
)


def get_metric_catalog() -> dict[str, dict[str, Any]]:
    """Obtiene metadatos de las métricas desde el catálogo real de XM."""
    catalog = ReadDB().get_collections()
    required = {"MetricId", "Entity", "Type", "MaxDays", "Url", "MetricUnits"}
    missing = required.difference(catalog.columns)
    if missing:
        raise ValueError(f"Faltan campos en el catálogo XM: {sorted(missing)}")

    metrics: dict[str, dict[str, Any]] = {}
    for metric_id in METRIC_IDS:
        rows = catalog[
            (catalog["MetricId"] == metric_id) & (catalog["Entity"] == ENTITY)
        ]
        if len(rows) != 1:
            raise LookupError(
                f"Se esperaba una fila para {metric_id}/{ENTITY}, "
                f"se encontraron {len(rows)}."
            )
        metric = rows.iloc[0].to_dict()
        if metric["Type"] != "DailyEntities":
            raise ValueError(
                f"{metric_id} dejó de ser diaria: {metric['Type']!r}."
            )
        metrics[metric_id] = metric
    return metrics


def windows(start: date, end: date):
    """Genera intervalos inclusivos de hasta 30 días calendario."""
    current = start
    while current <= end:
        window_end = min(current + timedelta(days=WINDOW_DAYS - 1), end)
        yield current, window_end
        current = window_end + timedelta(days=1)


def window_paths(output_dir: Path, start: date, end: date) -> tuple[Path, Path]:
    """Construye rutas deterministas para una respuesta y sus metadatos."""
    stem = f"{start.isoformat()}_{end.isoformat()}"
    return output_dir / f"{stem}.json", output_dir / f"{stem}_metadata.json"


def is_complete_window(raw_path: Path, start: date, end: date) -> bool:
    """Checks that a cached response has one observation for each requested day."""
    try:
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    items = payload.get("Items")
    if not isinstance(items, list):
        return False
    dates = []
    for item in items:
        entity_rows = item.get("DailyEntities", [])
        if not isinstance(entity_rows, list) or not any(
            row.get("Value") not in (None, "")
            for row in entity_rows
            if isinstance(row, dict)
        ):
            return False
        try:
            dates.append(date.fromisoformat(item["Date"]))
        except (KeyError, TypeError, ValueError):
            return False
    expected_dates = {
        start + timedelta(days=offset)
        for offset in range((end - start).days + 1)
    }
    return len(dates) == len(expected_dates) and set(dates) == expected_dates


def fetch_window(
    metric_id: str,
    metric: dict[str, Any],
    start: date,
    end: date,
) -> tuple[requests.Response, dict[str, Any]]:
    """Pide una ventana con reintentos limitados y espera creciente."""
    if (end - start).days + 1 > WINDOW_DAYS:
        raise ValueError("La ventana excede el máximo de 30 días.")

    body = {
        "MetricId": metric_id,
        "StartDate": start.isoformat(),
        "EndDate": end.isoformat(),
        "Entity": ENTITY,
        "Filter": [],
    }
    for attempt in range(len(RETRY_DELAYS_SECONDS) + 1):
        try:
            response = requests.post(
                str(metric["Url"]),
                json=body,
                timeout=(10, 90),
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(
                payload.get("Items"), list
            ):
                raise ValueError("La respuesta no contiene una lista Items.")
            return response, payload
        except (requests.RequestException, ValueError) as error:
            if attempt == len(RETRY_DELAYS_SECONDS):
                raise RuntimeError(
                    f"{metric_id} {start}–{end} falló tras "
                    f"{attempt + 1} intentos: {error}"
                ) from error
            delay = RETRY_DELAYS_SECONDS[attempt]
            LOGGER.warning(
                "%s %s–%s: intento %d falló (%s); reintento en %d s",
                metric_id,
                start,
                end,
                attempt + 1,
                error,
                delay,
            )
            time.sleep(delay)
    raise RuntimeError("La consulta terminó sin respuesta.")


def append_failure(
    output_dir: Path, metric_id: str, start: date, end: date, error: str
) -> None:
    """Registra el fallo de una ventana para facilitar su reanudación."""
    output_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "metric_id": metric_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "error": error,
    }
    with (output_dir / "failed_windows.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def store_response(
    output_dir: Path,
    metric_id: str,
    metric: dict[str, Any],
    start: date,
    end: date,
    response: requests.Response,
    payload: dict[str, Any],
) -> int:
    """Guarda el cuerpo JSON original y metadatos de la consulta."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path, metadata_path = window_paths(output_dir, start, end)
    raw_path.write_bytes(response.content)
    metadata = {
        "source": "API XM / pydataxm",
        "url": str(metric["Url"]),
        "parameters": {
            "MetricId": metric_id,
            "StartDate": start.isoformat(),
            "EndDate": end.isoformat(),
            "Entity": ENTITY,
            "Filter": [],
        },
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "http_status": response.status_code,
        "pydataxm_version": importlib.metadata.version("pydataxm"),
        "rows": len(payload["Items"]),
        "license": "Datos XM: por confirmar con XM",
        "attribution": "Fuente: XM",
        "catalog_metric": metric,
        "raw_response_file": raw_path.name,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return len(payload["Items"])


def download_metric(
    metric_id: str,
    metric: dict[str, Any],
    cutoff: date,
    output_root: Path,
    run_started: datetime,
) -> dict[str, Any]:
    """Descarga o reanuda las ventanas de una métrica."""
    output_dir = output_root / metric_id
    latest_window_start = max(
        start for start, end in windows(START_DATE, cutoff) if end == cutoff
    )
    refresh_after = date.today() - timedelta(days=RECENT_DAYS)
    downloaded = failed = empty = skipped = 0

    for start, end in windows(START_DATE, cutoff):
        raw_path, metadata_path = window_paths(output_dir, start, end)
        is_recent = end >= refresh_after or start == latest_window_start
        if raw_path.exists() and metadata_path.exists() and not is_recent:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            expected_rows = (end - start).days + 1
            if metadata.get("rows") != expected_rows or not is_complete_window(
                raw_path, start, end
            ):
                LOGGER.info(
                    "%s %s–%s: respuesta previa parcial; se volverá a consultar",
                    metric_id,
                    start,
                    end,
                )
            else:
                missing_metadata = False
                for key, value in (
                    ("license", "Datos XM: por confirmar con XM"),
                    ("attribution", "Fuente: XM"),
                ):
                    if key not in metadata:
                        metadata[key] = value
                        missing_metadata = True
                if missing_metadata:
                    metadata_path.write_text(
                        json.dumps(
                            metadata, ensure_ascii=False, indent=2, default=str
                        ),
                        encoding="utf-8",
                    )
                skipped += 1
                continue

        try:
            response, payload = fetch_window(metric_id, metric, start, end)
            row_count = store_response(
                output_dir, metric_id, metric, start, end, response, payload
            )
            downloaded += 1
            empty += row_count == 0
            LOGGER.info(
                "%s %s–%s: %d filas%s",
                metric_id,
                start,
                end,
                row_count,
                " (vacía; se reintentará en ejecuciones futuras)"
                if row_count == 0
                else "",
            )
        except Exception as error:
            failed += 1
            append_failure(output_dir, metric_id, start, end, str(error))
            LOGGER.error("%s", error)
        time.sleep(PAUSE_SECONDS)

    return {
        "metric_id": metric_id,
        "downloaded": downloaded,
        "failed": failed,
        "empty": empty,
        "skipped": skipped,
        "elapsed_seconds": (
            datetime.now(timezone.utc) - run_started
        ).total_seconds(),
    }


def inspect_saved_dates(output_dir: Path, cutoff: date) -> dict[str, Any]:
    """Resume dates from raw windows to report the stored coverage."""
    dates: list[date] = []
    for raw_path in output_dir.glob("*.json"):
        if raw_path.name.endswith("_metadata.json"):
            continue
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        for item in payload.get("Items", []):
            entity_rows = item.get("DailyEntities", [])
            if not isinstance(entity_rows, list) or not any(
                row.get("Value") not in (None, "")
                for row in entity_rows
                if isinstance(row, dict)
            ):
                continue
            try:
                day = date.fromisoformat(item["Date"])
            except (KeyError, TypeError, ValueError):
                continue
            if START_DATE <= day <= cutoff:
                dates.append(day)

    counts = Counter(dates)
    unique_dates = sorted(counts)
    missing = (cutoff - START_DATE).days + 1 - len(unique_dates)
    latest = unique_dates[-1] if unique_dates else None
    return {
        "first_date": unique_dates[0] if unique_dates else None,
        "last_date": latest,
        "days_expected": (cutoff - START_DATE).days + 1,
        "days_received": len(unique_dates),
        "missing_days": missing,
        "duplicate_days": sum(count - 1 for count in counts.values()),
        "lag_days": (date.today() - latest).days if latest else None,
    }


def parse_args() -> argparse.Namespace:
    """Define opciones acotadas para la descarga y su reanudación."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metric",
        choices=METRIC_IDS,
        action="append",
        help="Descarga solo esta métrica; puede repetirse.",
    )
    return parser.parse_args()


def main() -> int:
    """Descarga las cinco series diarias hasta el corte configurado."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    args = parse_args()
    run_started = datetime.now(timezone.utc)
    root = Path(__file__).resolve().parents[2]
    cutoff = load_data_cutoff(root)
    if cutoff > date.today():
        raise ValueError(f"data_cutoff {cutoff} no puede estar en el futuro.")

    metrics = get_metric_catalog()
    selected_ids = args.metric or list(METRIC_IDS)
    output_root = root / "data" / "raw" / "xm"
    results = []
    for metric_id in selected_ids:
        results.append(
            download_metric(
                metric_id,
                metrics[metric_id],
                cutoff,
                output_root,
                run_started,
            )
        )

    elapsed = (datetime.now(timezone.utc) - run_started).total_seconds()
    for result in results:
        coverage = inspect_saved_dates(
            output_root / result["metric_id"], cutoff
        )
        LOGGER.info(
            "%s: fechas=%s a %s; retraso=%s días; "
            "ventanas descargadas=%d, fallidas=%d, vacías=%d, omitidas=%d; "
            "días recibidos=%d/%d, faltantes=%d, duplicados=%d",
            result["metric_id"],
            coverage["first_date"],
            coverage["last_date"],
            coverage["lag_days"],
            result["downloaded"],
            result["failed"],
            result["empty"],
            result["skipped"],
            coverage["days_received"],
            coverage["days_expected"],
            coverage["missing_days"],
            coverage["duplicate_days"],
        )
    LOGGER.info("Tiempo total: %.1f s (%.1f min).", elapsed, elapsed / 60)
    return int(any(result["failed"] for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
