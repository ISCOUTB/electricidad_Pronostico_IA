"""Entrenamiento y evaluación temporal de las líneas base B0, B1 y B2."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
import yaml
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.evaluation.metrics import persistence_scale, regression_metrics


def _read_model_frame(path: Path) -> pd.DataFrame:
    """Carga una partición explícita y la ordena por target_date."""
    frame = pd.read_csv(path)
    required = {
        "target_date",
        "y_next",
        "price_t",
        "hydro_regime",
        "tipo_dia",
        "year",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{path.name} no contiene columnas requeridas: {sorted(missing)}")
    frame["target_date"] = pd.to_datetime(frame["target_date"], errors="raise")
    frame = frame.sort_values("target_date", kind="stable").reset_index(drop=True)
    if frame["target_date"].duplicated().any():
        raise ValueError(f"{path.name} tiene target_date duplicadas.")
    if frame[list(required)].isna().any().any():
        raise ValueError(f"{path.name} tiene nulos en columnas requeridas.")
    return frame


def _git_commit(project_root: Path) -> str:
    """Obtiene el commit actual para registrar la procedencia del experimento."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    """Calcula SHA-256 del archivo indicado."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pipeline(alpha: float | None = None) -> Pipeline:
    """Construye el Pipeline de Ridge con escalado ajustado dentro del fold."""
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("ridge", Ridge() if alpha is None else Ridge(alpha=alpha)),
        ]
    )


def _evaluate_subgroups(
    validation: pd.DataFrame,
    predictions: np.ndarray,
    mase_scale: float,
) -> dict[str, dict[str, dict[str, float]]]:
    """Calcula métricas dentro de cada categoría auditada."""
    output: dict[str, dict[str, dict[str, float]]] = {}
    for column in ("hydro_regime", "tipo_dia", "year"):
        groups: dict[str, dict[str, float]] = {}
        for value, indices in validation.groupby(column, sort=True).groups.items():
            positions = np.asarray(list(indices), dtype=int)
            groups[str(value)] = regression_metrics(
                validation.loc[positions, "y_next"].to_numpy(),
                predictions[positions],
                mase_scale,
            )
        output[column] = groups
    return output


def run_baselines(project_root: Path) -> dict[str, Any]:
    """Ajusta en train y evalúa en val, sin abrir otras particiones."""
    started_at = datetime.now(timezone.utc)
    config_path = project_root / "config" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    train_path = project_root / "data" / "processed" / "train.csv"
    val_path = project_root / "data" / "processed" / "val.csv"
    train = _read_model_frame(train_path)
    validation = _read_model_frame(val_path)

    train_end = pd.Timestamp(config["partitions"]["train"]["end"])
    val_start = pd.Timestamp(config["partitions"]["val"]["start"])
    val_end = pd.Timestamp(config["partitions"]["val"]["end"])
    if train["target_date"].max() != train_end:
        raise ValueError("train.csv no termina en el límite configurado.")
    if validation["target_date"].min() != val_start:
        raise ValueError("val.csv no empieza en el límite configurado.")
    if validation["target_date"].max() != val_end:
        raise ValueError("val.csv no termina en el límite configurado.")
    if train["target_date"].max() >= validation["target_date"].min():
        raise ValueError("Las fechas de train y val se solapan o están desordenadas.")

    feature_columns = config["feature_groups"]["price"]
    missing_train = set(feature_columns).difference(train.columns)
    missing_val = set(feature_columns).difference(validation.columns)
    if missing_train or missing_val:
        raise ValueError(
            f"Faltan variables price: train={sorted(missing_train)}, "
            f"val={sorted(missing_val)}."
        )

    x_train = train[feature_columns].to_numpy(dtype=float)
    y_train = train["y_next"].to_numpy(dtype=float)
    x_val = validation[feature_columns].to_numpy(dtype=float)
    y_val = validation["y_next"].to_numpy(dtype=float)
    mase_scale = persistence_scale(y_train)

    b0_strategy = config["baselines"]["B0"]["strategy"]
    b0 = DummyRegressor(strategy=b0_strategy)
    b0.fit(np.zeros((len(y_train), 1)), y_train)
    predictions: dict[str, np.ndarray] = {
        "B0": b0.predict(np.zeros((len(y_val), 1))),
        "B1": validation[config["baselines"]["B1"]["persistence_column"]].to_numpy(
            dtype=float
        ),
    }

    ridge_config = config["baselines"]["B2"]
    ridge_search = GridSearchCV(
        estimator=_pipeline(),
        param_grid={"ridge__alpha": ridge_config["alpha_grid"]},
        scoring=ridge_config["scoring"],
        cv=TimeSeriesSplit(n_splits=ridge_config["cv_splits"]),
        n_jobs=1,
        refit=True,
        return_train_score=False,
    )
    ridge_search.fit(x_train, y_train)
    predictions["B2"] = ridge_search.predict(x_val)

    validation_metrics = {
        model_name: {
            "global": regression_metrics(y_val, predicted, mase_scale),
            "subgroups": _evaluate_subgroups(validation, predicted, mase_scale),
        }
        for model_name, predicted in predictions.items()
    }
    best_reference = min(
        validation_metrics,
        key=lambda name: validation_metrics[name]["global"]["mae_cop_kwh"],
    )

    combined = pd.concat([train, validation], ignore_index=True)
    combined = combined.sort_values("target_date", kind="stable").reset_index(drop=True)
    combined_x = combined[feature_columns].to_numpy(dtype=float)
    combined_y = combined["y_next"].to_numpy(dtype=float)
    rolling_cv = TimeSeriesSplit(n_splits=ridge_config["cv_splits"])
    rolling_metrics: dict[str, list[dict[str, Any]]] = {"B1": [], "B2": []}
    for fold_number, (fit_indices, eval_indices) in enumerate(
        rolling_cv.split(combined_x), start=1
    ):
        fold_true = combined_y[eval_indices]
        fold_persistence = combined.iloc[eval_indices][
            config["baselines"]["B1"]["persistence_column"]
        ].to_numpy(dtype=float)
        fold_ridge = _pipeline(alpha=float(ridge_search.best_params_["ridge__alpha"]))
        fold_ridge.fit(combined_x[fit_indices], combined_y[fit_indices])
        fold_ridge_prediction = fold_ridge.predict(combined_x[eval_indices])
        rolling_metrics["B1"].append(
            {
                "fold": fold_number,
                "start_target_date": combined.iloc[eval_indices]["target_date"].min().date().isoformat(),
                "end_target_date": combined.iloc[eval_indices]["target_date"].max().date().isoformat(),
                "mae_cop_kwh": float(np.mean(np.abs(fold_true - fold_persistence))),
            }
        )
        rolling_metrics["B2"].append(
            {
                "fold": fold_number,
                "start_target_date": combined.iloc[eval_indices]["target_date"].min().date().isoformat(),
                "end_target_date": combined.iloc[eval_indices]["target_date"].max().date().isoformat(),
                "mae_cop_kwh": float(np.mean(np.abs(fold_true - fold_ridge_prediction))),
            }
        )

    prediction_frame = pd.DataFrame(
        {
            "target_date": validation["target_date"].dt.strftime("%Y-%m-%d"),
            "y_true": y_val,
        }
    )
    for model_name, predicted in predictions.items():
        prediction_frame[f"y_pred_{model_name}"] = predicted
        prediction_frame[f"absolute_error_{model_name}"] = np.abs(y_val - predicted)

    predictions_dir = project_root / "experiments" / "predictions"
    predictions_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = predictions_dir / "baselines_val.csv"
    prediction_frame.to_csv(prediction_path, index=False)

    experiment = {
        "date": date.today().isoformat(),
        "created_at_utc": started_at.isoformat(),
        "seed": int(config["seed"]),
        "commit_hash": _git_commit(project_root),
        "data": {
            "train_file": "data/processed/train.csv",
            "train_sha256": _sha256(train_path),
            "train_rows": len(train),
            "validation_file": "data/processed/val.csv",
            "validation_sha256": _sha256(val_path),
            "validation_rows": len(validation),
        },
        "units": "COP/kWh, escala original",
        "mase_scale_train_persistence_cop_kwh": mase_scale,
        "parameters": {
            "B0": {"estimator": "DummyRegressor", "strategy": b0_strategy},
            "B1": {
                "estimator": "persistencia",
                "prediction": config["baselines"]["B1"]["persistence_column"],
            },
            "B2": {
                "estimator": "Ridge",
                "features": "config.feature_groups.price",
                "pipeline": ["StandardScaler", "Ridge"],
                "alpha_grid": ridge_config["alpha_grid"],
                "search_cv": (
                    f"TimeSeriesSplit(n_splits={ridge_config['cv_splits']}) en train"
                ),
                "scoring": ridge_config["scoring"],
                "best_alpha": float(ridge_search.best_params_["ridge__alpha"]),
                "best_cv_mae_cop_kwh": float(-ridge_search.best_score_),
            },
            "rolling_origin": {
                "data": "train.csv + val.csv, ordenados por target_date",
                "cv": f"TimeSeriesSplit(n_splits={ridge_config['cv_splits']})",
                "B2_alpha": float(ridge_search.best_params_["ridge__alpha"]),
            },
        },
        "validation_metrics": validation_metrics,
        "rolling_origin_mae": rolling_metrics,
        "reference_baseline": best_reference,
        "prediction_file": "experiments/predictions/baselines_val.csv",
        "versions": {
            "python": platform.python_version(),
            "numpy": importlib.metadata.version("numpy"),
            "pandas": importlib.metadata.version("pandas"),
            "scikit_learn": sklearn.__version__,
            "holidays": importlib.metadata.version("holidays"),
            "pyyaml": importlib.metadata.version("PyYAML"),
        },
    }

    experiments_dir = project_root / "experiments"
    experiments_dir.mkdir(parents=True, exist_ok=True)
    json_path = experiments_dir / f"baselines_{date.today().isoformat()}.json"
    json_path.write_text(
        json.dumps(experiment, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return experiment


def main() -> None:
    """Ejecuta B0/B1/B2 únicamente con train y val, e imprime resumen."""
    root = Path(__file__).resolve().parents[2]
    experiment = run_baselines(root)
    print("MAE, RMSE y MASE en validación (COP/kWh para MAE/RMSE):")
    print("| Línea base | MAE | RMSE | MASE | Mediana AE | Fracción top 30 |")
    print("|---|---:|---:|---:|---:|---:|")
    for model_name, result in experiment["validation_metrics"].items():
        metrics = result["global"]
        print(
            f"| {model_name} | {metrics['mae_cop_kwh']:.3f} | "
            f"{metrics['rmse_cop_kwh']:.3f} | {metrics['mase']:.3f} | "
            f"{metrics['median_absolute_error_cop_kwh']:.3f} | "
            f"{metrics['top_30_absolute_error_fraction']:.3%} |"
        )
    print(f"Línea base de referencia por MAE en val: {experiment['reference_baseline']}")
    print(f"Mejor alpha Ridge: {experiment['parameters']['B2']['best_alpha']}")
    print("MAE rolling-origin:")
    for model_name, folds in experiment["rolling_origin_mae"].items():
        print(
            f"  {model_name}: "
            + ", ".join(f"{fold['mae_cop_kwh']:.3f}" for fold in folds)
        )
    print(
        "Resultados: "
        f"experiments/baselines_{experiment['date']}.json; "
        "experiments/predictions/baselines_val.csv"
    )


if __name__ == "__main__":
    main()
