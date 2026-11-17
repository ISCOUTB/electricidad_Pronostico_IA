"""Pruebas de alineación temporal y ausencia de fuga de información."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import holidays
import numpy as np
import pandas as pd
import pytest

from src.data.prepare_dataset import (
    START_DATE,
    add_auxiliary_columns,
    build_feature_frame,
    load_daily_wide,
    split_dataset,
)
from src.data.project_config import load_data_cutoff, load_project_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def prepared_inputs():
    config = load_project_config(ROOT)
    cutoff = load_data_cutoff(ROOT)
    daily_wide = load_daily_wide(ROOT / "data" / "raw", cutoff)
    feature_frame = build_feature_frame(daily_wide, config)
    labeled = feature_frame.dropna(subset=["y_next"]).copy()
    labeled, cutoffs = add_auxiliary_columns(labeled, config)
    partitions = split_dataset(labeled, config)
    return config, daily_wide, feature_frame, labeled, partitions, cutoffs


def test_truncation_does_not_change_features(
    prepared_inputs,
):
    """Recalcula 20 fechas usando solo historia hasta cada fecha."""
    config, daily_wide, full_features, _, _, _ = prepared_inputs
    columns = [
        column
        for group_columns in config["feature_groups"].values()
        for column in group_columns
    ]
    eligible_dates = full_features["date"].tolist()
    rng = np.random.default_rng(config["seed"])
    chosen_dates = rng.choice(eligible_dates, size=20, replace=False)

    for day in chosen_dates:
        day = str(day)
        day_index = pd.Timestamp(day)
        history_only = daily_wide.loc[:day_index]
        truncated_features = build_feature_frame(history_only, config)
        full_row = full_features.loc[full_features["date"] == day, columns].iloc[0]
        truncated_row = truncated_features.loc[
            truncated_features["date"] == day, columns
        ].iloc[0]
        pd.testing.assert_series_equal(
            full_row,
            truncated_row,
            check_names=False,
            check_exact=True,
        )


def test_partitions_are_contiguous_non_overlapping_and_complete(
    prepared_inputs,
):
    """Comprueba que target_date forma una secuencia continua entre los cortes."""
    _, _, _, labeled, partitions, _ = prepared_inputs
    date_sets = {
        name: set(pd.to_datetime(frame["target_date"]))
        for name, frame in partitions.items()
    }
    assert date_sets["train"].isdisjoint(date_sets["val"])
    assert date_sets["train"].isdisjoint(date_sets["test"])
    assert date_sets["val"].isdisjoint(date_sets["test"])

    all_dates = sorted(set.union(*date_sets.values()))
    assert all_dates == list(
        pd.date_range(all_dates[0], all_dates[-1], freq="D")
    )
    assert len(all_dates) == len(labeled)
    assert all_dates[0] == pd.Timestamp("2015-01-31")
    assert all_dates[-1] == pd.Timestamp("2026-11-09")


def test_y_next_is_not_a_predictor(prepared_inputs):
    """y_next, target_date y auxiliares no aparecen en los grupos de predictores."""
    config, _, _, labeled, _, _ = prepared_inputs
    feature_columns = {
        column
        for group_columns in config["feature_groups"].values()
        for column in group_columns
    }
    assert "y_next" not in feature_columns
    assert not any("y_next" in column for column in feature_columns)
    assert {"target_date", *config["auxiliary_columns"]}.isdisjoint(
        feature_columns
    )
    assert {"y_next", "target_date", *config["auxiliary_columns"]}.issubset(
        labeled.columns
    )


def test_partition_sizes_match_configuration(prepared_inputs):
    """Comprueba los tamaños declarados para train, val y test."""
    config, _, _, _, partitions, _ = prepared_inputs
    assert set(partitions) == {"train", "val", "test"}
    for name, bounds in config["partitions"].items():
        assert len(partitions[name]) == bounds["expected_rows"]


def test_holidays_supports_colombia_2026():
    """Verifica que los festivos colombianos de enero y diciembre se reconozcan."""
    colombia_2026 = holidays.country_holidays("CO", years=[2026])
    assert date(2026, 1, 1) in colombia_2026
    assert date(2026, 12, 25) in colombia_2026


def test_raw_alignment_is_exact(prepared_inputs):
    """Comprueba 4.331 fechas sin huecos ni nulos en el panel crudo."""
    _, daily_wide, _, _, _, _ = prepared_inputs
    cutoff = load_data_cutoff(ROOT)
    expected = pd.date_range(START_DATE, cutoff, freq="D", name="date")
    assert daily_wide.index.equals(expected)
    assert len(daily_wide) == 4331
    assert not daily_wide.isna().any().any()
