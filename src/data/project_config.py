"""Lectura mínima de los valores compartidos de configuración del proyecto."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml


def load_project_config(project_root: Path) -> dict[str, Any]:
    """Carga la configuración YAML compartida por los scripts del proyecto."""
    config_path = project_root / "config" / "config.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(f"No existe la configuración: {config_path}")

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"La configuración no es un mapa YAML: {config_path}")
    return config


def load_data_cutoff(project_root: Path) -> date:
    """Lee y valida data_cutoff de config/config.yaml."""
    config = load_project_config(project_root)
    value = config.get("data_cutoff")
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise ValueError("data_cutoff inválido en config/config.yaml") from error
