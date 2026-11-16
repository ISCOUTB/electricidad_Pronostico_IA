# Pronóstico del precio de bolsa de la electricidad en Colombia

Proyecto final de Inteligencia Artificial — Ruta C: aprendizaje automático con CRISP-ML(Q).

## Estado

Exploración inicial de las métricas de XM. La propuesta del proyecto se encuentra en [`docs/propuesta.md`](docs/propuesta.md).

## Estructura

Los datos de ejemplo consultados a XM se guardan en `data/raw/xm_samples/`. No se han entrenado modelos.

## Requisitos

Python ≥ 3.10.4. Las dependencias fijadas están en `requirements.txt`.

## Explorar el catálogo y muestras de XM

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.data.explore_xm
```
