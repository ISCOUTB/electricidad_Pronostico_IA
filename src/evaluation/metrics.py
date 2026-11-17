"""Métricas de regresión para el pronóstico en escala original."""

from __future__ import annotations

from typing import Any

import numpy as np


def persistence_scale(y_train: Any) -> float:
    """Calcula MAE de persistencia como media de diferencias absolutas en train."""
    values = np.asarray(y_train, dtype=float).reshape(-1)
    if len(values) < 2:
        raise ValueError("Se necesitan al menos dos observaciones de train para MASE.")
    if not np.isfinite(values).all():
        raise ValueError("y_train contiene valores no finitos.")
    scale = float(np.mean(np.abs(np.diff(values))))
    if scale <= 0:
        raise ValueError("La escala de persistencia de train debe ser positiva.")
    return scale


def regression_metrics(y_true: Any, y_pred: Any, mase_scale: float) -> dict[str, float]:
    """Devuelve MAE, RMSE, MASE, mediana AE y fracción de error del top 30."""
    actual = np.asarray(y_true, dtype=float).reshape(-1)
    predicted = np.asarray(y_pred, dtype=float).reshape(-1)
    if actual.shape != predicted.shape or actual.size == 0:
        raise ValueError("y_true e y_pred deben tener la misma longitud no vacía.")
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("Las predicciones y valores reales deben ser finitos.")
    if not np.isfinite(mase_scale) or mase_scale <= 0:
        raise ValueError("mase_scale debe ser finita y positiva.")

    absolute_errors = np.abs(actual - predicted)
    total_absolute_error = float(absolute_errors.sum())
    largest_errors = np.sort(absolute_errors)[-min(30, len(absolute_errors)) :]
    top_30_fraction = (
        float(largest_errors.sum() / total_absolute_error)
        if total_absolute_error > 0
        else 0.0
    )
    mae = float(absolute_errors.mean())
    return {
        "mae_cop_kwh": mae,
        "rmse_cop_kwh": float(np.sqrt(np.mean(np.square(actual - predicted)))),
        "mase": float(mae / mase_scale),
        "median_absolute_error_cop_kwh": float(np.median(absolute_errors)),
        "top_30_absolute_error_fraction": top_30_fraction,
    }
