"""Explora el catálogo de métricas de XM y guarda muestras crudas."""

from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from pydataxm.pydataxm import ReadDB

LOGGER = logging.getLogger("explore_xm")
REQUIRED_COLUMNS = {
    "MetricId",
    "MetricName",
    "Entity",
    "MaxDays",
    "Type",
    "Url",
    "Filter",
    "MetricUnits",
    "MetricDescription",
}
TARGETS = {
    "precio_bolsa_nacional": ("precio", "bolsa", "nacional"),
    "demanda_real_sin": ("demanda real",),
    "aportes_hidricos": ("aportes", "energia"),
    "media_historica_aportes": ("aportes", "media", "historica", "energia"),
    "volumen_util_embalses": ("volumen", "util", "diario", "energia"),
}
GRANULARITY = {"HourlyEntities": "horaria", "DailyEntities": "diaria"}


def normalize_text(value: Any) -> str:
    """Normaliza tildes y espacios para buscar nombres del catálogo."""
    text = unicodedata.normalize("NFKD", str(value))
    return " ".join(
        "".join(char for char in text if not unicodedata.combining(char))
        .casefold()
        .split()
    )


def locate_targets(catalog: pd.DataFrame) -> dict[str, pd.Series]:
    """Encuentra las métricas del SIN usando sus nombres reales del catálogo."""
    missing_columns = REQUIRED_COLUMNS.difference(catalog.columns)
    if missing_columns:
        raise ValueError(
            "El catálogo de XM no contiene las columnas esperadas. "
            f"Columnas recibidas: {catalog.columns.tolist()}; "
            f"faltantes: {sorted(missing_columns)}"
        )

    system_metrics = catalog[
        catalog["Entity"].map(normalize_text).eq("sistema")
    ]
    selected: dict[str, pd.Series] = {}
    for target, terms in TARGETS.items():
        candidates = system_metrics[
            system_metrics["MetricName"].map(
                lambda name: all(term in normalize_text(name) for term in terms)
            )
        ]
        if candidates.empty:
            raise LookupError(
                f"No se encontró '{target}' en el catálogo actual. "
                f"Revise los nombres impresos arriba."
            )
        if len(candidates) > 1:
            names = candidates["MetricName"].tolist()
            LOGGER.warning(
                "Hay varias métricas para %s; se selecciona la primera del "
                "catálogo: %s. Candidatas: %s",
                target,
                names[0],
                names,
            )
        selected[target] = candidates.iloc[0]
    return selected


def collect_iso_dates(value: Any) -> list[date]:
    """Busca fechas ISO en cualquier nivel de la respuesta sin normalizarla."""
    found: list[date] = []
    if isinstance(value, dict):
        for nested in value.values():
            found.extend(collect_iso_dates(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(collect_iso_dates(nested))
    elif isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            found.append(date.fromisoformat(value))
        except ValueError:
            pass
    return found


def safe_filename(value: str) -> str:
    """Convierte nombres del catálogo en nombres de archivo portables."""
    normalized = normalize_text(value)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def save_sample(
    target: str,
    metric: pd.Series,
    start_date: date,
    end_date: date,
    output_dir: Path,
) -> None:
    """Consulta y archiva una respuesta XM sin transformar su contenido."""
    if (end_date - start_date).days >= 30:
        raise ValueError("La ventana solicitada excede 30 días calendario.")

    data_type = str(metric["Type"])
    if data_type not in GRANULARITY:
        raise ValueError(
            f"Granularidad no compatible para {metric['MetricName']}: {data_type}"
        )

    endpoint = str(metric["Url"]).strip()
    request_body = {
        "MetricId": str(metric["MetricId"]),
        "StartDate": start_date.isoformat(),
        "EndDate": end_date.isoformat(),
        "Entity": str(metric["Entity"]),
        "Filter": [],
    }
    filename = f"{target}_{safe_filename(request_body['MetricId'])}"
    response = requests.post(endpoint, json=request_body, timeout=(10, 60))

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"{filename}.json"
    metadata_path = output_dir / f"{filename}_metadata.json"
    raw_path.write_bytes(response.content)
    metadata = {
        "source": "XM API",
        "url": endpoint,
        "request": request_body,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "data_license": "Por confirmar con XM",
        "attribution": "Fuente: XM. La licencia de los datos está por confirmar.",
        "catalog_metric": metric.to_dict(),
        "raw_response_file": raw_path.name,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    response.raise_for_status()

    payload = response.json()
    LOGGER.info("Respuesta real para %s: %s", target, json.dumps(payload, ensure_ascii=False))
    dates = collect_iso_dates(payload)
    LOGGER.info(
        "%s: granularidad %s; entidad/cruce %s / %s; ventana pedida %s–%s; "
        "primera fecha observada en la muestra: %s; guardado en %s",
        target,
        GRANULARITY[data_type],
        metric["Entity"],
        metric["Filter"],
        start_date,
        end_date,
        min(dates).isoformat() if dates else "sin fechas ISO reconocibles",
        raw_path,
    )


def main() -> int:
    """Lista el catálogo, explora cinco métricas y guarda sus muestras crudas."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    client = ReadDB()
    catalog = client.get_collections()
    if catalog.empty:
        raise RuntimeError("XM devolvió un catálogo vacío.")
    LOGGER.info("Catálogo real de XM (%d filas):\n%s", len(catalog), catalog.to_string(index=False))

    selected = locate_targets(catalog)
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "data" / "raw" / "xm_samples"
    end_date = datetime.now(timezone.utc).date() - timedelta(days=1)
    start_date = end_date - timedelta(days=29)
    failures: list[str] = []

    for index, (target, metric) in enumerate(selected.items()):
        data_type = str(metric["Type"])
        LOGGER.info(
            "\nMétrica localizada: %s | %s | %s | entidad/cruce: %s / %s "
            "| máximo catálogo: %s días",
            target,
            metric["MetricId"],
            metric["MetricName"],
            metric["Entity"],
            metric["Filter"],
            metric["MaxDays"],
        )
        try:
            save_sample(target, metric, start_date, end_date, output_dir)
        except requests.RequestException as error:
            LOGGER.error("Falló la consulta de %s: %s", target, error)
            failures.append(target)
        if index < len(selected) - 1:
            time.sleep(1)

    LOGGER.info(
        "\nEl catálogo consultado no declara la fecha histórica inicial de cada "
        "métrica. Las fechas reportadas son las primeras observadas en la "
        "ventana consultada, no una afirmación del inicio histórico."
    )
    if failures:
        LOGGER.error("Consultas fallidas: %s", ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
