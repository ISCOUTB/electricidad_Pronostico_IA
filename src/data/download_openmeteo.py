"""Descarga clima diario ERA5 de Open-Meteo para los puntos del proyecto."""

from __future__ import annotations

import json
import logging
import math
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

LOGGER = logging.getLogger("download_openmeteo")
API_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "America/Bogota"
MODEL = "era5"
START_DATE = date(2015, 1, 1)
DAILY_VARIABLES = (
    "temperature_2m_mean",
    "temperature_2m_max",
    "precipitation_sum",
)
POINTS = {
    "barranquilla": {"latitude": 10.96, "longitude": -74.80},
    "bogota": {"latitude": 4.71, "longitude": -74.07},
    "medellin": {"latitude": 6.25, "longitude": -75.56},
    "cali": {"latitude": 3.45, "longitude": -76.53},
    "guatape_el_penol": {"latitude": 6.2, "longitude": -75.2},
    "guavio": {"latitude": 4.8, "longitude": -73.5},
}
REQUEST_TIMEOUT = (10, 120)
RETRY_DELAYS_SECONDS = (2, 4, 8)
POINT_PAUSE_SECONDS = 2


def build_parameters(coordinates: dict[str, float], end_date: date) -> dict[str, Any]:
    """Construye la consulta con el modelo y la zona horaria fijados."""
    return {
        **coordinates,
        "start_date": START_DATE.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": TIMEZONE,
        "models": MODEL,
    }


def load_cached_response(
    raw_path: Path, metadata_path: Path, parameters: dict[str, Any]
) -> dict[str, Any] | None:
    """Usa una respuesta previa solo si corresponde exactamente a esta consulta."""
    if not raw_path.exists() or not metadata_path.exists():
        return None

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("parameters") != parameters or metadata.get("http_status") != 200:
        return None
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    LOGGER.info("Usando respuesta en caché: %s", raw_path)
    return payload


def request_archive(parameters: dict[str, Any]) -> tuple[requests.Response, dict[str, Any]]:
    """Consulta la API con reintentos acotados y espera creciente."""
    for attempt in range(len(RETRY_DELAYS_SECONDS) + 1):
        try:
            response = requests.get(API_URL, params=parameters, timeout=REQUEST_TIMEOUT)
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            payload = response.json()
            return response, payload
        except (requests.RequestException, ValueError) as error:
            if attempt == len(RETRY_DELAYS_SECONDS):
                raise RuntimeError(
                    f"Open-Meteo falló después de {attempt + 1} intentos: {error}"
                ) from error
            delay = RETRY_DELAYS_SECONDS[attempt]
            LOGGER.warning(
                "Consulta fallida (intento %d/%d): %s. Reintento en %d s.",
                attempt + 1,
                len(RETRY_DELAYS_SECONDS) + 1,
                error,
                delay,
            )
            time.sleep(delay)
    raise RuntimeError("La consulta terminó sin respuesta.")


def validate_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Comprueba esquema, variables solicitadas y calendario local."""
    if payload.get("timezone") != TIMEZONE:
        raise ValueError(
            f"Zona horaria inesperada: {payload.get('timezone')!r}; "
            f"se esperaba {TIMEZONE!r}."
        )
    if payload.get("utc_offset_seconds") != -18_000:
        raise ValueError(
            "Open-Meteo no devolvió el desfase UTC−5 esperado para Colombia: "
            f"{payload.get('utc_offset_seconds')!r}."
        )

    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise ValueError("La respuesta no contiene el objeto 'daily'.")
    missing = {"time", *DAILY_VARIABLES}.difference(daily)
    if missing:
        raise ValueError(f"Faltan campos diarios en la respuesta: {sorted(missing)}.")

    dates = daily["time"]
    if not isinstance(dates, list):
        raise ValueError("El campo daily.time no es una lista.")
    for variable in DAILY_VARIABLES:
        values = daily[variable]
        if not isinstance(values, list) or len(values) != len(dates):
            raise ValueError(
                f"Longitud incoherente para {variable}: "
                f"{len(values) if isinstance(values, list) else 'no es lista'} "
                f"valores y {len(dates)} fechas."
            )
    return daily


def trailing_null_count(values: list[Any]) -> int:
    """Cuenta los valores nulos consecutivos al final de la serie."""
    count = 0
    for value in reversed(values):
        if value is not None:
            break
        count += 1
    return count


def summarize_point(
    point_name: str,
    parameters: dict[str, Any],
    payload: dict[str, Any],
    daily: dict[str, Any],
) -> None:
    """Imprime cobertura, faltantes y rarezas sin modificar la respuesta cruda."""
    dates = daily["time"]
    valid_dates: list[str] = []
    for index, day in enumerate(dates):
        if any(daily[variable][index] is not None for variable in DAILY_VARIABLES):
            valid_dates.append(day)

    print(f"\n{point_name} — coordenadas solicitadas: "
          f"{parameters['latitude']}, {parameters['longitude']}")
    print(
        f"  Calendario de respuesta: {dates[0] if dates else 'sin fechas'} a "
        f"{dates[-1] if dates else 'sin fechas'} ({len(dates)} filas); "
        f"fechas con algún dato: {valid_dates[0] if valid_dates else 'ninguna'} a "
        f"{valid_dates[-1] if valid_dates else 'ninguna'}."
    )
    print(
        f"  Zona devuelta: {payload['timezone']} "
        f"(UTC{payload['utc_offset_seconds'] // 3600:+03d}:00); "
        f"modelo solicitado: {MODEL}; coordenada de grilla: "
        f"{payload.get('latitude')}, {payload.get('longitude')}."
    )

    for variable in DAILY_VARIABLES:
        values = daily[variable]
        null_count = sum(value is None for value in values)
        trailing = trailing_null_count(values)
        available = [
            (day, value)
            for day, value in zip(dates, values)
            if value is not None
        ]
        latest = available[-1][0] if available else "ninguna"
        finite_values = [
            float(value)
            for value in values
            if isinstance(value, (int, float)) and math.isfinite(float(value))
        ]
        is_constant = len(finite_values) >= 2 and len(set(finite_values)) == 1
        details = [
            f"nulos={null_count}",
            f"nulos finales consecutivos={trailing}",
            f"último dato válido={latest}",
            f"constante={'sí' if is_constant else 'no'}",
        ]
        if variable == "precipitation_sum":
            negative_count = sum(value < 0 for value in finite_values)
            details.append(f"precipitación negativa={negative_count}")
        print(f"  {variable}: " + "; ".join(details))


def save_point(point_name: str, coordinates: dict[str, float], root: Path) -> None:
    """Carga desde caché o descarga y guarda respuesta y metadatos de un punto."""
    end_date = datetime.now(ZoneInfo(TIMEZONE)).date()
    parameters = build_parameters(coordinates, end_date)
    point_dir = root / "data" / "raw" / "openmeteo" / point_name
    raw_path = point_dir / "response.json"
    metadata_path = point_dir / "_metadata.json"
    payload = load_cached_response(raw_path, metadata_path, parameters)

    if payload is None:
        response, payload = request_archive(parameters)
        daily = validate_response(payload)
        point_dir.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(response.content)
        metadata = {
            "source": "Open-Meteo Historical Weather API",
            "model": MODEL,
            "url": API_URL,
            "parameters": parameters,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "http_status": response.status_code,
            "rows": len(daily["time"]),
            "requested_coordinates": coordinates,
            "returned_grid_coordinates": {
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude"),
            },
            "timezone": payload.get("timezone"),
            "utc_offset_seconds": payload.get("utc_offset_seconds"),
            "license": "CC BY 4.0",
            "attribution": "Weather data by Open-Meteo.com",
            "raw_response_file": raw_path.name,
        }
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"\nRespuesta real de {point_name}: claves raíz "
            f"{list(payload.keys())}; claves diarias {list(daily.keys())}; "
            f"primeras filas "
            f"{json.dumps({key: value[:3] for key, value in daily.items()}, ensure_ascii=False)}"
        )
    else:
        daily = validate_response(payload)
        if not raw_path.exists():
            raise FileNotFoundError(f"No existe la respuesta cruda: {raw_path}")

    summarize_point(point_name, parameters, payload, daily)


def main() -> None:
    """Descarga o reutiliza los seis históricos diarios configurados."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    root = Path(__file__).resolve().parents[2]
    for index, (point_name, coordinates) in enumerate(POINTS.items()):
        save_point(point_name, coordinates, root)
        if index < len(POINTS) - 1:
            time.sleep(POINT_PAUSE_SECONDS)


if __name__ == "__main__":
    main()
