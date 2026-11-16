# Pronóstico a un día del precio de bolsa de la electricidad en Colombia con aprendizaje automático (XM + clima)

_Proyecto final de Inteligencia Artificial · Hito 1 — Propuesta · Ruta C: Aprendizaje automático (CRISP-ML(Q)) · Noviembre de 2026_

**Integrantes:** [Nombre 1] · [Nombre 2] · [Nombre 3]   |   **Curso / docente:** [Curso] · [Docente]

## 1. Problema y usuario

**Usuario:** comercializadores de energía, usuarios no regulados y gestores de compras expuestos al precio de bolsa (precio spot horario único del SIN). **Problema:** el precio es muy volátil y se agudiza con El Niño. Según XM (vía El Colombiano), el precio máximo en bolsa pasó de $285,30/kWh (31-dic-2025) a $900,82/kWh (3-jul-2026) y el ponderado subió 155 % [1]; en julio el kWh se compró en bolsa a $797,7 frente a $334,2 en contratos, y las empresas que atienden hogares y pequeños comercios tenían en promedio 23 % de su energía expuesta a bolsa [2]. El sector además enfrenta problemas financieros, incluidos los de Air-e intervenida (Caribe) [1]. Hoy la referencia pública disponible es el precio ya liquidado de días anteriores. **Pregunta:** ¿mejoran las variables hidro-climáticas (aportes y embalses de XM, clima observado) el pronóstico del precio del día siguiente frente a (a) repetir el precio de hoy y (b) modelos que solo usan la historia del propio precio, y en qué regímenes (seco/húmedo, año) falla el modelo?

## 2. Formulación como tarea de aprendizaje automático

**Tarea:** regresión supervisada de serie temporal. **Salida:** precio de bolsa nacional del día t+1 (COP/kWh), agregado diario de la serie horaria (promedio simple; si la API entrega el ponderado diario oficial se usará ese, decisión de Hito 2 previa a cualquier modelado). **Entradas (día t):** rezagos y estadísticos móviles del precio (1–30 días), demanda, aportes hídricos y su razón a la media histórica, volumen útil de embalses, clima observado hasta t en ~5–6 puntos (Caribe: Barranquilla/Cartagena; centros de demanda; zonas de aporte hídrico; a fijar y justificar en Hito 2) y calendario de t+1 (día de la semana, festivo). **Regla anti-fuga:** solo información disponible al cierre de t (sin ofertas/despacho ni clima de t+1). **PEAS —** P: MAE del pronóstico a 1 día; E: mercado mayorista parcialmente observable, estocástico, secuencial y dinámico, con cambio de régimen; A: pronóstico mostrado al usuario en el prototipo; S: API de XM y Open-Meteo.

## 3. Datos, licencias y partición

| Fuente | Variables | Acceso | Licencia / autorización |
|---|---|---|---|
| API XM (Sinergox) | Precio de bolsa nacional, demanda del SIN, aportes hídricos y media histórica, volumen útil de embalses | POST a servapibi.xm.com.co o librería pydataxm (MIT); sin usuario ni clave; máx. 30 días por llamada horaria/diaria (≈145 llamadas por variable) | Datos públicos del operador; términos de reutilización por confirmar con XM antes del Hito 2; se cita la fuente en todo producto [4] |
| Open-Meteo (histórico ERA5) | Temperatura, precipitación y otras variables diarias en los puntos elegidos | API REST sin llave, uso no comercial, ≲10 000 llamadas/día (respaldo: NASA POWER) | CC BY 4.0; atribución «Weather data by Open-Meteo.com» [5] |

**Periodo:** 2015-01-01 hasta el último dato disponible (≈4 300 días); series agregadas, **sin datos personales**. **Partición cronológica** (nunca aleatoria): entrenamiento 2015-01-01 → 2022-12-31 (≈2 900 d, incluye El Niño 2015–16); validación 2023-01-01 → 2024-12-31 (≈730 d, incluye El Niño 2023–24); prueba 2025-01-01 → último dato (≈650 d, incluye el alza de 2026), usada **una sola vez**. El preprocesamiento se ajusta solo con entrenamiento (Pipeline) y el ajuste de hiperparámetros usa validación de ventana móvil (TimeSeriesSplit, 5 pliegues).

## 4. Línea base y comparación mínima de la Ruta C

**Líneas base:** B0 DummyRegressor (media del entrenamiento; equivale al clasificador mayoritario en regresión); B1 persistencia (ŷ(t+1) = y(t)); B2 Ridge sobre rezagos (regresión lineal regularizada). La línea base de referencia es la de menor MAE en validación. **Modelos propuestos (≥2):** M1 Random Forest y M2 Gradient Boosting (scikit-learn), con ajuste de hiperparámetros por búsqueda aleatoria y el mismo presupuesto para ambos; 5 semillas, media ± desviación. **Ablación:** con vs. sin variables hidro-climáticas. La elección de la técnica se justifica con el libro guía (aprendizaje supervisado, cap. 19–21 del enunciado), CRISP-ML(Q) [3] y literatura en el informe.

## 5. Evaluación declarada antes de experimentar

**Métrica primaria:** MAE en prueba (COP/kWh, siempre en escala original aunque el modelo use transformación). **Secundarias:** RMSE (penaliza picos), MASE respecto a persistencia y MAE por subgrupo. **Subgrupos:** régimen hidrológico (aportes/media histórica, terciles), tipo de día (hábil vs. fin de semana/festivo) y año calendario (deriva). **Umbral de éxito:** (i) MAE en prueba del mejor modelo ≤ 0,90 × MAE en prueba de la mejor línea base, es decir mejora ≥ 10 %; y (ii) el modelo supera a la persistencia en ≥ 4 de 5 pliegues de la validación de ventana móvil. Si no se cumple, se reporta tal cual y se analiza por qué; cualquier cambio posterior de métrica, umbral o partición se justifica por escrito.

## 6. Riesgos principales y prototipo

Fuga temporal; cambio de régimen y deriva (El Niño, nivel nominal de precios); cobertura geográfica del clima; uso del pronóstico como asesoría financiera (el prototipo mostrará error esperado y limitaciones). **Prototipo:** app Streamlit/Gradio que carga el modelo ya entrenado y muestra pronóstico, comparación con la línea base y atribución de datos.

## Referencias

[1] A. Villamizar, «Precio de la energía en bolsa se dispara 285 % y alertan riesgos por el fenómeno de El Niño», El Colombiano, 6-jul-2026. elcolombiano.com/negocios/precio-energia-en-bolsa-fenomeno-el-nino-KM38524709  
[2] «Alerta por tarifas de energía: estas empresas están más expuestas al alza de precios ante el fenómeno de El Niño», Infobae, 15-sep-2026. infobae.com/colombia/2026/09/15/alerta-por-tarifas-de-energia-estas-empresas-estan-mas-expuestas-al-alza-de-precios-ante-el-fenomeno-de-el-nino/  
[3] S. Studer et al., «Towards CRISP-ML(Q): A Machine Learning Process Model with Quality Assurance Methodology», Mach. Learn. Knowl. Extr., vol. 3, n.º 2, pp. 392–413, 2021, doi: 10.3390/make3020020.  
[4] XM, «API XM / pydataxm», github.com/EquipoAnaliticaXM/API_XM (licencia MIT del código).  
[5] Open-Meteo.com Weather API, CC BY 4.0, doi: 10.5281/zenodo.7970649.  
