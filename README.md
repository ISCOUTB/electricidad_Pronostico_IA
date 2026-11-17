# Pronóstico del precio de bolsa de la electricidad en Colombia

Proyecto final de Inteligencia Artificial — Ruta C: aprendizaje automático con CRISP-ML(Q).

## Estado

Preparación de datos para el pronóstico de precio de bolsa nacional diario. La propuesta del proyecto se encuentra en [`docs/propuesta.md`](docs/propuesta.md).

## Estructura

Los datos crudos de XM y Open-Meteo están en `data/raw/`; la preparación produce el panel diario y las particiones en `data/interim/` y `data/processed/`. No se han entrenado modelos. Uso citando la fuente XM (confirmado por el equipo, 2026-11-16).

## Requisitos

Python ≥ 3.10.4. Las dependencias fijadas están en `requirements.txt`.

## Explorar el catálogo y muestras de XM

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.data.explore_xm
```

## Preparar el dataset

```powershell
.\.venv\Scripts\python.exe -m src.data.prepare_dataset
.\.venv\Scripts\python.exe -m pytest
```

## Evaluar líneas base (solo train y val)

```powershell
.\.venv\Scripts\python.exe -m src.models.baselines
```
