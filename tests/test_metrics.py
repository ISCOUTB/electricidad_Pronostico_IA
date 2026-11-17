"""Pruebas enfocadas para la escala MASE y métricas de error."""

import numpy as np
import pytest

from src.evaluation.metrics import persistence_scale, regression_metrics


def test_persistence_scale_uses_train_first_differences():
    assert persistence_scale([1, 3, 2, 8]) == pytest.approx(3.0)


def test_regression_metrics_are_in_original_units():
    result = regression_metrics([10, 20, 30], [8, 25, 29], mase_scale=4)
    assert result["mae_cop_kwh"] == pytest.approx(8 / 3)
    assert result["rmse_cop_kwh"] == pytest.approx(np.sqrt(10))
    assert result["mase"] == pytest.approx(2 / 3)
    assert result["median_absolute_error_cop_kwh"] == pytest.approx(2)
    assert result["top_30_absolute_error_fraction"] == pytest.approx(1)


def test_top_30_fraction_is_share_of_total_absolute_error():
    errors = np.arange(1, 36, dtype=float)
    result = regression_metrics(errors, np.zeros_like(errors), mase_scale=1)
    assert result["top_30_absolute_error_fraction"] == pytest.approx(615 / 630)
