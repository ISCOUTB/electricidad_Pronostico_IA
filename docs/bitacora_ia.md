# Bitácora humano-IA — energy_prediccion

<!-- Nota de edición: cada integrante registra sus propios usos de IA. Antes de cada entrega, revisa que la columna «Cómo se verificó» describa lo que realmente se hizo; el docente puede preguntarlo en la sustentación. -->

## Declaración de uso de IA generativa

Se usaron dos herramientas de IA generativa: **Claude** (Anthropic) para planificación, comparación de dominios, verificación de fuentes y APIs, redacción de los hitos y de los prompts de trabajo; y **GitHub Copilot** (agente en VS Code) para implementar scripts, pruebas y documentación de datos. El equipo revisa y ejecuta todo lo generado antes de integrarlo, y cada integrante registra aquí sus propios usos.

## Registro de usos

| N.º | Fecha | Integrante | Herramienta | Para qué se usó | Qué se aceptó, modificó o descartó | Cómo se verificó |
|---|---|---|---|---|---|---|
| 1 | 2026-11-16 | Sebastian Torres | Claude | Lectura del enunciado y redacción de un `copilot-instructions.md` ampliado (reglas de la rúbrica, CRISP-ML(Q), reglas de datos, bitácora, sustentación) en reemplazo del generado por `/init`. | Aceptado como configuración del agente. Corregido después: fechas erróneas (caso 3). | Su efecto se observó en Copilot: se detuvo en las condiciones de parada de los prompts y no usó `test.csv` en las líneas base. |
| 2 | 2026-11-16 | Sebastian Torres | Claude | Propuesta de cuatro dominios para la Ruta C con verificación de APIs gratuitas (XM, Open-Meteo, NASA POWER, datos.gov.co, OpenAQ). | Aceptado: dominio de energía (precio de bolsa). Descartados: agro, lluvias intensas y calidad del aire. La elección fue del equipo. | Las APIs se comprobaron con scripts propios: XM devolvió su catálogo (193 métricas) y Open-Meteo 4.338 filas por punto. |
| 3 | 2026-11-16 | Sebastian Torres | Claude | Redacción del Hito 1 (formulación, partición cronológica, líneas base, métrica primaria y umbral) y de `docs/propuesta.md`. | Aceptado. La licencia de XM quedó pendiente y se resolvió después (uso citando la fuente). | Revisión por el equipo y aprobación del docente. |
| 4 | 2026-11-16 | Sebastian Torres | Copilot | Andamiaje del repositorio: carpetas, `.gitignore`, `.env.example`, README y `requirements.txt`. | Aceptado. | Revisión manual de lo creado y de `git status`: sin datos crudos ni claves en el control de versiones. |
| 5 | 2026-11-16 | Sebastian Torres | Copilot | `src/data/explore_xm.py`: listar el catálogo de XM y guardar muestras crudas de 30 días de cinco métricas. | Aceptados el script y las muestras. | El integrante ejecutó el script, abrió una muestra para ver cómo llegan las 24 horas y revisó `git diff`. |
| 6 | 2026-11-16 | Sebastian Torres | Copilot | Revisión del catálogo completo de XM y sondeo de cobertura desde 2015-01-01. | Aceptado: objetivo = `PPPrecBolsNaci` (ponderado diario oficial). Descartado: agregar a mano las 24 horas de `PrecBolsNaci`. | El agente se detuvo al hallar la métrica (condición del prompt); el sondeo de 2015 devolvió 30 días para las cinco métricas. |
| 7 | 2026-11-16 | Sebastian Torres | Copilot | Descargadores de XM (725 ventanas, idempotentes, con metadatos) y de Open-Meteo (ERA5, 6 puntos) y reporte de calidad. | Aceptados, con `data_cutoff: 2026-11-09` y `DemaSIN` en lugar de sumar `DemaReal` (la suma horaria no coincide exactamente y fue mucho menor el 11 y 12 de noviembre). | Reporte: 4.331 de 4.331 días por métrica, sin huecos, duplicados, negativos ni ceros; la segunda pasada reutilizó lo descargado; revisión manual de JSON crudos (unidades y fecha inicial) y de las coordenadas de Guatapé y Guavio en un mapa. |
| 8 | 2026-11-16 | Sebastian Torres | Copilot | `prepare_dataset.py`: alineación de fuentes, 53 variables en cinco grupos, partición por fecha objetivo, diccionario de datos y pruebas anti-fuga. | Aceptados: conjuntos S0/S1/S2, terciles de régimen hídrico solo con train y `holidays` 0.108 (MIT). | Seis pruebas pasan (incluye truncamiento en ≥20 fechas); conteos 2.892/731/678 y 16/23/53 variables coinciden con lo previsto antes de ejecutar; `pip check` sin incompatibilidades. |
| 9 | 2026-11-16 | Sebastian Torres | Copilot | Líneas base B0, B1 y B2 (`metrics.py`, `baselines.py`) evaluadas solo en validación, con ventana móvil y registro del experimento. | Aceptado: B1 (persistencia) como línea base de referencia, MAE 66,27 COP/kWh. | Tres pruebas de métricas pasan; los SHA-256 de train y val coinciden con el JSON; ningún script referencia `test.csv`; revisión manual de resultados. |
| 10 | 2026-11-16 | Sebastian Torres | Claude | Hipótesis: los días con precio casi idéntico (noviembre de 2024) se deberían a un tope regulatorio, por ejemplo el precio de escasez. | Descartada (caso 1). | Se descargó `PrecEscaAct` (936,06 el 1 y el 3 de noviembre de 2024) y se comparó con `PPPrecBolsNaci` (2.459,24): no coinciden. |
| 11 | 2026-11-16 | Sebastian Torres | Claude | Redacción de los prompts 2 a 7 para el agente de Copilot. | Aceptados y ejecutados; el agente respetó las condiciones de parada. | Los resultados se contrastaron con lo previsto: filas por conjunto, número de variables y condiciones de parada. |
| 12 | 2026-11-16 | Sebastian Torres | Claude | Redacción del Hito 2 y de esta bitácora a partir de los reportes de Copilot. | Aceptados tras revisión; se incluyeron los nombres del equipo. | El integrante contrastó las cifras con los reportes originales de Copilot. |

## Casos en que la IA propuso algo incorrecto o inadecuado

Base para la reflexión de media página del informe.

**Caso 1 — Hipótesis del tope de precio (Claude).** Ante valores idénticos de `PPPrecBolsNaci` (2.459,24 el 1 y el 3 de noviembre de 2024), propuso que reflejaban un tope regulatorio como el precio de escasez. Era una explicación plausible sin respaldo en los datos. **Detección:** al compararlo con `PrecEscaAct` (936,06) no coincidía. La causa de los valores repetidos sigue sin explicar y se investigará en el análisis de errores.

**Caso 2 — Expectativa sobre el periodo de prueba (Claude).** En el Hito 1 planteó la prueba (2025–2026) como la de mayor cambio de régimen por el alza de 2026. Los datos muestran que el máximo (2.499 COP/kWh) está en 2024, dentro de validación, y que la prueba llega a 1.032. **Detección:** mínimos y máximos por año del reporte de calidad. **Consecuencia:** el MAE de validación está dominado por 2024 y no es directamente comparable con el de prueba; se reportará por año.

**Caso 3 — Fecha incorrecta (Claude).** El archivo de instrucciones y su registro de decisiones llevaban la fecha 2026-11-05, pero el trabajo y los experimentos son del 2026-11-16. **Detección:** al comparar con las marcas de fecha de los experimentos. Se corrige reemplazando la fecha.
