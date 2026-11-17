# energy_prediccion — Pronóstico a un día del precio de bolsa de la electricidad en Colombia (XM + clima)

_Proyecto final de Inteligencia Artificial · Hito 2 — Avance · Ruta C: Aprendizaje automático (CRISP-ML(Q)) · Noviembre de 2026_

**Integrantes:** Sebastian Andres Torres Ortega · Luis Gustavo Ruiz Teran

## 1. Estado frente a lo comprometido en el Hito 1

| Compromiso | Estado | Evidencia en el repositorio |
|---|---|---|
| Datos listos | Hecho | `data/processed/{train,val,test}.csv`; diccionario de datos en `data/README.md` |
| Línea base ejecutándose | Hecho | `src/models/baselines.py`: B0, B1 y B2 evaluadas solo en validación |
| Primer resultado en el repositorio | Hecho | `experiments/baselines_2026-11-16.json` y predicciones de validación |
| Reproducible con el README | Documentado | README con la ejecución de punta a punta; 9 pruebas automáticas pasan (6 anti-fuga, 3 de métricas) |
| Métrica, umbral y partición | Sin cambios | Tal como se declararon en el Hito 1; registro de decisiones en `.github/copilot-instructions.md` §19 |

## 2. Datos construidos

Dataset de pronóstico a un día con **4.331 días contiguos** (2015-01-01 → corte 2026-11-09), sin huecos ni nulos, a partir de 5 series de XM (objetivo **PPPrecBolsNaci**; DemaSIN, AporEner, AporEnerMediHist y VoluUtilDiarEner) y 6 puntos de Open-Meteo/ERA5 (Barranquilla, Bogotá, Medellín, Cali, Guatapé/El Peñol y Guavio). Tras descartar 30 filas (29 sin ventana de 30 días y 1 sin objetivo t+1) quedan 4.301: **train 2.892 · val 731 · test 678**, particionadas por fecha objetivo. Hay 53 variables (precio 11, demanda 2, calendario 3, hidrología 7, clima 30); los conjuntos de ablación S0/S1/S2 tienen 16/23/53. **Prevención de fuga:** toda variable usa datos hasta t (el calendario de t+1 se conoce de antemano), los terciles del régimen hídrico se calculan solo con train y hay pruebas automáticas, incluido un truncamiento en ≥20 fechas. **Licencias:** XM, uso citando la fuente (confirmado por el equipo); Open-Meteo, CC BY 4.0.

**Ajustes (sin tocar métrica, umbral ni partición):** (a) el objetivo es el precio ponderado diario oficial de XM, opción prevista en el Hito 1, por lo que no se promedian 24 horas; (b) el corte 2026-11-09 es el último día válido en Open-Meteo, así que la prueba tiene 678 días (≈650 estimados); (c) ERA5 (~25 km) suaviza los puntos de montaña; (d) XM publica con ≈7 días de rezago, por lo que el prototipo trabajará sobre fechas históricas.

## 3. Primer resultado: líneas base en validación (2023–2024)

| Línea base | MAE (COP/kWh) | RMSE | MASE* | MAE 2023 | MAE 2024 |
|---|---|---|---|---|---|
| B0 — media del entrenamiento | 410,40 | 552,89 | 22,32 | 352,09 | 468,54 |
| **B1 — persistencia (referencia)** | **66,27** | 140,01 | 3,60 | 47,58 | 84,92 |
| B2 — Ridge sobre rezagos de precio (α = 10) | 70,08 | 142,95 | 3,81 | 52,65 | 87,45 |

*MASE con escala de la persistencia en train (18,39 COP/kWh). **Lectura:** la persistencia es la línea base de referencia y Ridge no la mejora, ni en el global ni en ninguno de los 5 pliegues de la validación de ventana móvil. Que la MASE de la persistencia sea 3,6 indica que la validación es mucho más volátil que el entrenamiento. El error es muy desigual: en B1 el MAE de 2024 (84,9) casi duplica el de 2023 (47,6); el régimen hídrico medio (82,1) supera al alto (47,7) y al bajo (66,1); tipo de día casi no pesa (hábil 66,5 vs. no laboral 65,9); los 30 días de mayor error aportan 31,3 % del error total; y el MAE por pliegue de B1 crece de 9,5 a 73,5. Los extremos de precio (máx. 2.499 COP/kWh, en 2024) están en validación, mientras que la prueba llega a 1.032: el MAE de validación y el de prueba no serán directamente comparables. **Referencia indicativa:** 0,90 × 66,27 ≈ 59,6 COP/kWh; el criterio formal del Hito 1 se evalúa en prueba, una sola vez.

## 4. Riesgos y próximos pasos hacia el Hito 3

**Próximos pasos:** Random Forest y Gradient Boosting con ajuste de hiperparámetros (TimeSeriesSplit) y 5 semillas; ablación S0/S1/S2; evaluación única en prueba; análisis de ≥10 errores; métricas por subgrupo e IA responsable; prototipo; informe IEEE. **Riesgos:** la persistencia es una referencia muy fuerte, así que el umbral de mejora ≥10 % es exigente y no se modificará; la volatilidad cambia entre periodos (deriva); el rezago de publicación de XM limita cualquier demo «en vivo».

## 5. Bitácora de uso de IA

La bitácora completa está en docs/bitacora_ia.md. Se registran 12 usos de dos herramientas (Claude y GitHub Copilot) y 3 casos en que la IA propuso algo incorrecto o inadecuado. Las primeras entradas se adjuntan en el anexo.
