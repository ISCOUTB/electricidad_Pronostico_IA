# Instrucciones de Copilot — Proyecto final de IA (Ruta C: Aprendizaje automático)

> **Versión:** 3 · **Actualizado:** 2026-11-05 · **Fase actual:** Hito 1 redactado, pendiente de aprobación del docente (dominio: energía)
> Este archivo es la fuente de verdad para el asistente. Se edita a medida que el proyecto avanza: cuando cambie algo (dominio, métrica, estructura, comandos), actualiza la sección correspondiente **en el mismo commit** que el cambio.

---

## 0. Cómo leer y usar este archivo

- **Idioma:** responde siempre en **español**. Identificadores de código en **inglés** (`snake_case`); comentarios, docstrings, README, bitácora y mensajes de commit en **español**.
- **Orden de lectura antes de trabajar:** (1) §1 Estado del proyecto, (2) el enunciado del curso (`Propósito y resultados de aprendiza.md`; si se mueve, actualizar esta ruta), (3) `docs/propuesta.md` cuando exista, (4) `README.md` y `config/`.
- Si falta una definición (dominio, métrica, umbral, partición), **no la asumas en silencio**: propónla marcada como `PROPUESTO – pendiente de aprobación` o haz **una** pregunta concreta.
- **No inventes** comandos, archivos de configuración, endpoints, nombres de campos de una API, IDs de conjuntos de datos, versiones de librerías, DOIs, referencias ni resultados. Si no lo sabes o no lo has ejecutado, dilo.

---

## 1. Estado del proyecto (EDITAR al avanzar)

| Campo | Valor |
|---|---|
| Ruta principal | **C — Aprendizaje automático**, metodología CRISP-ML(Q) |
| Equipo | POR DEFINIR (2–3 integrantes; cada uno debe poder explicar cualquier parte) |
| Dominio | **Energía** — precio de bolsa de la electricidad en Colombia (XM + clima) |
| Usuario y problema real | Comercializadores, usuarios no regulados y gestores de compras expuestos al precio spot horario del SIN. Volátil y agudizado por El Niño: el precio máximo pasó de $285,30 a $900,82/kWh entre el 31-dic-2025 y el 3-jul-2026 (El Colombiano, 6-jul-2026). Fuentes completas en `docs/propuesta.md`. |
| Pregunta que responde el proyecto | ¿Mejoran las variables hidro-climáticas el pronóstico del precio del día siguiente frente a repetir el precio de hoy y a modelos que solo usan la historia del precio? ¿En qué regímenes falla? |
| Tarea de aprendizaje | Regresión supervisada de serie temporal, horizonte t+1 |
| Variable objetivo | Precio de bolsa nacional diario (COP/kWh): promedio simple de las 24 horas, o el ponderado diario oficial si la API lo entrega. Se fija en el Hito 2, antes de modelar, y no cambia después. |
| Fuentes de datos (APIs) y licencias | API XM (precio de bolsa, demanda, aportes y media histórica, volumen útil) · Open-Meteo histórico ERA5, CC BY 4.0 (respaldo: NASA POWER). Sin datos personales. Licencia de los datos de XM por confirmar. |
| Periodo y partición | 2015-01-01 → último dato. **Cronológica:** entrenamiento 2015-01-01→2022-12-31 · validación 2023-01-01→2024-12-31 · prueba 2025-01-01→fin. La prueba se usa una sola vez. Ajuste con `TimeSeriesSplit` (5 pliegues). |
| Línea base | B0 `DummyRegressor` (media) · B1 persistencia ŷ(t+1)=y(t) · B2 Ridge sobre rezagos. La de referencia es la de menor MAE en validación. |
| Modelos a comparar (≥2) | Random Forest y Gradient Boosting (scikit-learn), mismo presupuesto de búsqueda, 5 semillas. Ablación: con vs. sin variables hidro-climáticas. |
| **Métrica primaria y umbral de éxito** | **MAE en prueba (COP/kWh, escala original).** Éxito = (i) MAE del mejor modelo ≤ 0,90 × MAE de la mejor línea base **y** (ii) supera a la persistencia en ≥4 de 5 pliegues de ventana móvil. Declarado en el Hito 1; no cambiar sin justificación escrita (§19). |
| Métricas secundarias | RMSE, MASE (respecto a persistencia), MAE por subgrupo |
| Subgrupos a auditar | Régimen hidrológico (aportes/media histórica, terciles) · tipo de día (hábil vs. fin de semana/festivo) · año calendario (deriva) |
| Prototipo | Streamlit o Gradio (a decidir): pronóstico + comparación con la línea base + error esperado + atribución de datos |

### Hitos

Cada hito se sube como archivo independiente: `nombre_proyecto_hito1.pdf`, `..._hito2.pdf`, `..._hito3.pdf`, `..._hito4` (el enunciado dice «.pdf (presentación en ppt)»: **confirmar con el docente el formato**). Fechas: completar con el calendario del curso. Los hitos 1 y 2 no suman puntos, pero **no entregarlos a tiempo descuenta 5 puntos cada uno**.

- [ ] **Hito 1 — Propuesta (1 página).** *Estado: PDF redactado (`precio_bolsa_energia_hito1.pdf`), pendiente de aprobación del docente.* Problema y usuario, ruta elegida, fuente de datos con licencia, línea base prevista, métricas y umbral de éxito declarados antes de experimentar. *Condición: aprobación del docente (alcance y datos viables). Sin propuesta aprobada no hay proyecto.*
- [ ] **Hito 2 — Avance.** Datos listos, línea base ejecutándose, primer resultado en el repositorio; una página de avance + primeras entradas de la bitácora IA. *Condición: la línea base se reproduce siguiendo el README.*
- [ ] **Hito 3 — Entrega final (85 pts, criterios 1–8).** Informe IEEE, repositorio completo, prototipo funcional, bitácora IA. *Condición: repositorio ejecutable y comparación mínima de la ruta completa.*
- [ ] **Hito 4 — Sustentación (15 pts, criterio 9, nota individual).** 20 min: presentación 8 + demo en vivo 4 (caso propuesto por el docente) + preguntas 8 (incluye una modificación en vivo).

---

## 2. Contexto y objetivo

Proyecto final de IA: llevar un problema real hasta una solución de IA **funcional, evaluada con evidencia y defendida oralmente**. No se evalúa la herramienta sino la calidad del razonamiento: *por qué esa técnica, cómo se midió y qué limitaciones tiene*. Se valoran los problemas del contexto local (Cartagena, Caribe, Colombia).

**Ruta C (Aprendizaje automático):** núcleo = aprendizaje supervisado o no supervisado con CRISP-ML(Q) (cap. 19–21 según el enunciado).

- Línea base mínima: clasificador mayoritario, regresión lineal o regresión logística.
- Comparación mínima: **≥2 modelos + ajuste de hiperparámetros**.
- Métricas típicas: F1, AUC, RMSE, matriz de confusión, **métricas por subgrupo**.

**Estrategia de datos del equipo:** construir un **dataset crudo propio** a partir de llamadas a **APIs gratuitas**, y sobre él implementar el ciclo completo de CRISP-ML(Q). Un script que solo llama a una API sin diseño, datos propios ni evaluación **no cumple**.

---

## 3. Reglas no negociables (lo que más puntos cuesta)

1. **Métrica y umbral antes de experimentar.** Se declaran en `docs/propuesta.md` (Hito 1). No se cambian en silencio.
2. **Siempre hay línea base.** Nunca se reporta un modelo solo. Toda tabla de resultados incluye la línea base.
3. **≥2 modelos además de la línea base + ajuste de hiperparámetros**, con el mismo presupuesto de búsqueda para todos.
4. **El conjunto de prueba se usa una sola vez**, al final. Jamás para elegir modelo, hiperparámetros, umbrales ni variables.
5. **Cero fuga de datos.** Partir **antes** de preprocesar; transformadores ajustados solo con entrenamiento; sin variables del futuro; sin duplicados entre particiones.
6. **Semillas fijas** (una sola constante en `config/`) y **varias corridas o validación cruzada**, reportando media ± desviación.
7. **Datos con fuente, licencia y fecha de descarga documentadas.** Sin datos personales identificables.
8. **≥10 errores del sistema analizados y clasificados**, con hipótesis de causa (apuntar a ≥15 por margen).
9. **Métricas por subgrupo** (región, ciudad, estación del año, etc.) y análisis de IA responsable **específico del caso**.
10. **Prototipo ejecutable** que carga un modelo ya entrenado; no reentrena al correr.
11. **Todo uso de IA se declara** en `docs/bitacora_ia.md`, incluyendo al menos un caso donde la IA se equivocó.
12. **Todo lo entregado debe poder explicarse.** Código que el equipo no entienda = falta de integridad académica. Preferir código simple y legible sobre código ingenioso.

---

## 4. Metodología CRISP-ML(Q) → qué se hace y dónde queda

Referencia obligatoria (cuenta como artículo científico en el informe): S. Studer *et al.*, «Towards CRISP-ML(Q): A Machine Learning Process Model with Quality Assurance Methodology,» *Mach. Learn. Knowl. Extr.*, vol. 3, n.º 2, pp. 392–413, 2021, doi: 10.3390/make3020020. El modelo tiene seis fases y aplica aseguramiento de calidad (riesgos + métodos de mitigación) en cada una.

| Fase | Qué se hace | Aseguramiento de calidad | Evidencia en el repo |
|---|---|---|---|
| 1. Comprensión del negocio y de los datos | Problema, usuario, criterios de éxito (de negocio y de ML), factibilidad, disponibilidad y licencias de datos | Riesgos de cobertura, representatividad y licencias; restricciones de cómputo | `docs/propuesta.md`, `data/README.md`, `docs/crispml_q.md` |
| 2. Preparación de datos | Selección, limpieza, variables derivadas, partición | Esquema validado, sin fuga, reproducible, decisiones documentadas | `src/data/`, `src/features/`, `data/processed/` |
| 3. Modelado | Línea base; ≥2 modelos; ajuste de hiperparámetros | Misma partición y presupuesto para todos; semillas; cada corrida registrada | `src/models/`, `experiments/` |
| 4. Evaluación | Prueba (una vez), subgrupos, robustez, explicabilidad, análisis de errores | Comparar contra los criterios de éxito declarados; conclusiones ≤ evidencia | `experiments/`, `docs/errores.md` |
| 5. Despliegue | Prototipo que carga el modelo guardado; guía de uso | Probar con casos nuevos y entradas inválidas; modo sin conexión | `app/`, `README.md` |
| 6. Monitoreo y mantenimiento | Plan: qué vigilar (deriva de datos y de desempeño) y cuándo reentrenar | Limitaciones y deriva documentadas; chequeo de deriva simple (opcional) | Sección del informe, `docs/crispml_q.md` |

`docs/crispml_q.md` es un registro vivo: por fase, tareas hechas, riesgos identificados, mitigación y enlace a la evidencia. Alimenta los criterios 1, 2 y 3 de la rúbrica.

---

## 5. Estructura del repositorio

Obligatorio según el enunciado: `README.md`, `requirements.txt` (versiones fijadas), `data/`, `src/`, `notebooks/`, `experiments/`, `docs/bitacora_ia.md`. El resto es recomendado. **Crear cada carpeta cuando se use, no antes.**

```
.
├── README.md              # descripción + instalación y ejecución en < 5 comandos
├── requirements.txt       # versiones fijadas (==) y versión de Python declarada
├── .env.example           # solo nombres de variables, nunca valores reales
├── .gitignore
├── config/config.yaml     # semilla, rutas, parámetros de API, partición, hiperparámetros
├── data/
│   ├── raw/               # respuestas crudas de las APIs. INMUTABLE: no se edita a mano
│   ├── interim/
│   ├── processed/         # train / val / test
│   └── README.md          # diccionario de datos, fuentes, licencias, fechas de descarga
├── src/
│   ├── data/              # download_*.py, build_dataset.py, split.py
│   ├── features/
│   ├── models/            # baseline.py, train.py, tune.py
│   ├── evaluation/        # metrics.py, subgroups.py, error_analysis.py
│   └── utils/
├── notebooks/             # exploración (EDA). Lo que importa se migra a src/
├── experiments/           # un JSON/CSV por corrida: semilla, parámetros, métricas, commit
├── models/                # artefactos serializados pequeños (joblib)
├── app/                   # prototipo (Streamlit / Gradio / CLI)
├── tests/                 # solo para lo crítico (partición sin fuga, métricas, esquema)
└── docs/
    ├── propuesta.md       # fuente del PDF del Hito 1
    ├── hito2_avance.md
    ├── bitacora_ia.md
    ├── crispml_q.md
    ├── errores.md
    ├── ia_responsable.md
    └── informe/           # fuentes del informe IEEE y figuras
```

Preferir estructura simple y explicable sobre andamiaje complejo. No agregar CI, Docker, linters ni frameworks de experimentos salvo que el equipo lo pida.

---

## 6. Datos: de la API al dataset

### 6.1 Reglas de ingesta

- **Un script por fuente** en `src/data/`, idempotente (volver a correrlo no duplica ni corrompe) y con **caché** de las respuestas crudas.
- Guardar cada respuesta cruda en `data/raw/<fuente>/<AAAA-MM-DD>/` junto con un `_metadata.json`: URL base, parámetros, fecha y hora UTC, código HTTP, licencia y atribución requerida.
- **Inspecciona la respuesta real antes de escribir el parser** (imprime claves y primeras filas). Las APIs cambian; no confíes en la memoria del asistente sobre campos o endpoints.
- Respetar límites de uso: pausas, reintentos con *backoff* y fragmentación de rangos grandes de fechas. Nunca bucles sin límite.
- **Valores centinela** (p. ej. `-999` en NASA POWER) → convertir a `NaN` de forma explícita y documentada.
- Llaves y tokens **solo** en `.env` (cargadas por variable de entorno); jamás en el código ni en commits. `.env.example` lleva solo los nombres.
- Si `data/raw/` pesa demasiado para Git: subir el script de descarga y una muestra pequeña en `data/sample/`.
- Estadísticas descriptivas y diccionario de datos → `data/README.md` (alimentan la sección 5 del informe).

### 6.2 Reglas por fuente (aplicar solo a las que se usen; verificado 2026-11-05, reconfirmar términos antes del Hito 1)

| Fuente | Acceso | Reglas |
|---|---|---|
| **Open-Meteo** (clima histórico ERA5, calidad del aire, etc.) | Sin llave | Gratis solo para **uso no comercial**; límites de uso justo ≈ 10 000 llamadas/día, 5 000/h, 600/min. Datos **CC BY 4.0**: mostrar «Weather data by Open-Meteo.com» con enlace en el prototipo y el informe. |
| **NASA POWER** (clima y radiación diarios desde 1981) | Sin autenticación | Citar el proyecto POWER; el sitio indica licencia CC BY 4.0. Faltantes = `-999`. |
| **datos.gov.co** (Socrata/SODA: IDEAM, EVA agropecuarias, etc.) | Lectura pública; token de app opcional | Endpoint tipo `https://www.datos.gov.co/resource/<id>.json`. Paginar con `$limit`/`$offset` y `$order` estable. **Revisar la licencia en la ficha de cada conjunto.** Verificar cobertura temporal real del conjunto antes de depender de él. |
| **XM** (API Sinergox, sector eléctrico) | Sin usuario ni clave. `pydataxm` (MIT, requiere Python ≥ 3.10.4) o POST a `https://servapibi.xm.com.co/{hourly,daily,monthly,lists}` con `MetricId`, `StartDate`, `EndDate`, `Entity` | **Máx. 30 días por llamada** en datos horarios y diarios (731 mensuales, 366 anuales): fragmentar y dejar pausas. Listar las métricas reales (`get_collections()` o endpoint `lists` con `ListadoMetricas`) **antes** de fijar nombres o granularidad. Licencia de los datos **por confirmar con XM** antes del Hito 2; citar siempre la fuente. |
| **OpenAQ v3** (calidad del aire) | Llave gratuita (`X-API-Key`) | ≈ 60 solicitudes/min y 2 000/h. **Cobertura desigual**: verificar que existan estaciones en la zona antes de comprometerse. |

### 6.3 Partición y fuga de datos

- La estrategia se **decide y justifica en el Hito 1** y vive en `config/`:
  - Datos temporales → partición **cronológica** (entrenamiento < validación < prueba, con separación si hay rezagos) y `TimeSeriesSplit` para validación cruzada. **Nunca mezcla aleatoria.**
  - Unidades espaciales (estaciones, municipios) → partición **agrupada** si el objetivo es generalizar a lugares nuevos.
  - Clases desbalanceadas → partición **estratificada**.
- Todo preprocesamiento (imputación, escalado, codificación, selección de variables) dentro de un `sklearn.pipeline.Pipeline` ajustado **solo** con entrenamiento.
- **Lista de chequeo de fuga:** objetivo derivado de variables de entrada · ventanas móviles que miran al futuro · normalizar/imputar con todo el dataset · seleccionar variables con todo el dataset · duplicados entre particiones · ajustar umbrales con la prueba · sobremuestreo (SMOTE) antes de partir.

### 6.4 Reglas específicas del proyecto (precio de bolsa)

- **Solo información disponible al cierre del día t** para predecir t+1: rezagos, aportes, embalses, demanda, clima observado y calendario de t+1. Por decisión de diseño se **excluyen** las ofertas/despacho de t+1 y el clima de t+1 (fuga).
- El precio de bolsa se forma **hora a hora**; el objetivo diario se agrega de la serie horaria. Fijar la definición (promedio simple vs. ponderado) en el Hito 2 y **no cambiarla** después.
- Métricas siempre en **COP/kWh, escala original**, aunque el modelo use logaritmo u otra transformación.
- Los precios son nominales y hay **cambio de régimen** (El Niño 2015–16 en entrenamiento, 2023–24 en validación, alza de 2026 en prueba): reportar MAE por año y tratar la deriva como hallazgo, no como ruido. Nunca reajustar umbrales mirando la prueba.
- Las ventanas móviles solo miran hacia atrás; ninguna variable se deriva del objetivo de t+1.
- Clima: fijar y justificar en el Hito 2 los ~5–6 puntos (centros de demanda, incluido el Caribe, y zonas de aporte hídrico). Open-Meteo/ERA5 es reanálisis, no observación directa: documentarlo como limitación.
- Atribución visible en prototipo e informe: «Weather data by Open-Meteo.com» y la fuente XM.

---

## 7. Modelado y experimentación

- **Línea base (obligatoria):** `DummyClassifier(strategy="most_frequent")` o `DummyRegressor`, **más** un modelo lineal simple (regresión logística / lineal / Ridge). En series temporales, añadir línea base ingenua (persistencia o climatología).
- **Modelos a comparar (≥2):** elegir con justificación frente a al menos una alternativa, citando el libro guía o un artículo. Empezar por scikit-learn (p. ej. Random Forest, gradient boosting). **Evitar aprendizaje profundo** salvo que se justifique, y **evitar AutoML de caja negra** (no se puede defender).
- **Ajuste de hiperparámetros:** `GridSearchCV` / `RandomizedSearchCV` / Optuna con validación cruzada solo sobre entrenamiento+validación. Registrar espacio de búsqueda y mejores parámetros. **Mismo presupuesto para todos los modelos.**
- **Varias corridas:** ≥5 semillas o k-fold; reportar media ± desviación estándar.
- **Desbalance:** `class_weight`, estratificación, PR-AUC; cualquier remuestreo **solo dentro** de los pliegues de entrenamiento.
- **Explicabilidad:** importancia por permutación (o SHAP) y dependencia parcial, para justificar el modelo y guiar el análisis de errores.
- **Probabilidades:** si se usan, revisar calibración (curva de calibración, Brier).
- **Registro de cada corrida** en `experiments/`: fecha, semilla, hash del commit, versión de los datos, parámetros, métricas. **Cada tabla del informe debe poder rastrearse a un archivo de `experiments/`.**
- Tiempo de entrenamiento razonable (minutos) en equipo personal, Colab o Kaggle: la demo y la modificación en vivo de la sustentación lo exigen.
- Hiperparámetros y reglas centralizados en `config/` para poder cambiarlos en vivo y **predecir el efecto antes de ejecutar**.

---

## 8. Evaluación y análisis de errores

- **Métrica primaria + umbral de éxito** (de §1) gobiernan la conclusión. Elegir métricas coherentes con la tarea:
  - Clasificación: F1 (de la clase de interés o macro), PR-AUC/ROC-AUC, matriz de confusión, exactitud balanceada. *Con desbalance, justificar por qué F1 y no exactitud.*
  - Regresión: RMSE, MAE, R²; cuidar MAPE con valores cercanos a cero.
  - Series temporales: comparar contra persistencia/climatología.
- **Tabla comparativa** modelo × métrica (media ± desviación), en validación y prueba, con la línea base incluida.
- **Métricas por subgrupo** y señalar las brechas.
- **Análisis de errores (≥10 casos, apuntar a ≥15)** en `docs/errores.md` + `experiments/errors/*.csv`. Por caso: ID, entradas relevantes, valor real, predicción, **tipo de error** y **hipótesis de causa** con evidencia. Taxonomía sugerida: calidad del dato · valor extremo/evento raro · cambio de distribución · variable faltante · ruido de etiqueta · desbalance · límite del modelo · sesgo espacial/temporal.
- **Conclusiones limitadas a la evidencia:** sin causalidad no demostrada, sin generalizar fuera del rango de los datos. Si el modelo no supera el umbral, se reporta tal cual y se analiza por qué.

---

## 9. IA responsable (riesgos específicos del caso, no genéricos)

Documentar en `docs/ia_responsable.md` y medir cuando sea posible:

- **Sesgo de representatividad:** zonas, estaciones o unidades con más datos dominan el ajuste → medir error por subgrupo.
- **Desempeño desigual** entre subgrupos → reportar brechas y proponer mitigación (ponderación, umbrales por grupo, más datos).
- **Cambio de distribución** en el tiempo (eventos climáticos, cambios de reporte) → validación temporal y análisis de deriva.
- **Privacidad:** usar datos agregados; no cruzar fuentes de modo que permita reidentificar personas.
- **Uso indebido y sobreconfianza:** la predicción no es una decisión; mostrar incertidumbre y limitaciones en el prototipo; no usar para decisiones automáticas de alto impacto.
- **Seguridad:** llaves en `.env`; validar entradas del prototipo.
- **Licencias y atribución** de todas las fuentes.
- **Costo y cómputo:** reportar recursos y tiempos (todo debe correr en recursos gratuitos).

Cada riesgo con **mitigación concreta**. Riesgos genéricos aplicables a cualquier proyecto se califican como «Básico».

---

## 10. Prototipo funcional

- App sencilla (Streamlit o Gradio), API o CLI. **Debe ejecutarse desde scripts**, no solo desde un notebook.
- Carga el **modelo y el preprocesamiento ya guardados**; no reentrena.
- Acepta **entradas nuevas** (el docente propone el caso en la sustentación; no se puede depender de un ejemplo precargado).
- Muestra: predicción, probabilidad/incertidumbre cuando aplique, **comparación con la línea base**, breve explicación y aviso de limitaciones. Incluye la **atribución de datos** requerida (§6.2).
- Maneja entradas inválidas sin romperse.
- **Modo sin conexión:** si la API falla durante la demo, usar datos en caché. Probar esto antes de la sustentación.

---

## 11. Reproducibilidad y calidad de código

- Python como lenguaje base; **≥ 3.10.4** (requisito de `pydataxm`), versión declarada en el README. `requirements.txt` con versiones fijadas (`==`).
- Semillas fijadas para `random`, `numpy` y los estimadores; una sola constante en `config/`.
- Rutas con `pathlib` y relativas a la raíz del repo; nunca rutas absolutas.
- `logging` en lugar de `print` en `src/`; funciones pequeñas con docstring (en español) y *type hints*.
- Notebooks solo para exploración. **La solución final corre desde `src/` o `app/`.**
- Comentar el **porqué** de las decisiones no obvias (partición, métrica, hiperparámetro), no el qué.
- Pruebas (si se agregan) con `python -m pytest`; solo para lo crítico. No añadir herramientas que el proyecto no use.

---

## 12. Git y trabajo en equipo

- **Historial distribuido en el tiempo y entre integrantes.** Un único commit la víspera de la entrega es señal de alerta.
- Commits pequeños y frecuentes, con prefijo: `datos:`, `modelo:`, `exp:`, `eval:`, `app:`, `docs:`, `fix:`.
- Una rama por integrante o tarea; revisión cruzada para que todos entiendan lo que se integra.
- **Nunca** commitear `.env`, llaves, datos personales ni archivos grandes. Mantener `.gitignore` al día.
- Etiquetar los hitos (`hito1`, `hito2`, `hito3`).
- Repositorio en GitHub/GitLab, público o compartido con el docente.

---

## 13. Bitácora humano-IA (`docs/bitacora_ia.md`)

Una fila por uso relevante de IA (Copilot, Claude, ChatGPT, Gemini u otros):

| Fecha | Integrante | Herramienta | Para qué se usó | Qué se aceptó / modificó / descartó | Cómo se verificó |
|---|---|---|---|---|---|

- **Regla para Copilot:** tras entregar código o texto sustantivo, recuerda registrarlo y propón un borrador de la fila. **«Cómo se verificó» lo completa el humano con lo que realmente hizo** (ejecutar, comparar con documentación, probar a mano); no lo rellenes tú.
- Mantener al final una lista **«Casos donde la IA se equivocó»** (qué propuso, por qué era incorrecto, cómo se detectó). Es la base de la reflexión de media página del informe.
- Usar IA sin declararla, o no poder explicar un fragmento en la sustentación, se trata como falta de integridad académica.

---

## 14. Informe técnico (formato IEEE, 2 columnas, 6–8 páginas sin referencias ni anexos; español o inglés)

1. Resumen (≤200 palabras) y palabras clave · 2. Introducción (problema, usuario, relevancia, pregunta) · 3. Trabajo relacionado (**≥5 referencias, ≥3 artículos científicos** de IEEE/ACM/Springer/Elsevier/ACL/arXiv revisado, **+ el libro guía**) · 4. Formulación (PEAS, tipo de entorno, definición formal de la tarea) · 5. Datos (origen, licencia, estadísticas, preprocesamiento) · 6. Método (línea base, técnica, alternativas, diagrama de arquitectura o secuencia) · 7. Experimentos y resultados (configuración, métricas, tabla comparativa, gráficos, análisis de errores) · 8. IA responsable y limitaciones · 9. Conclusiones y trabajo futuro (**respuesta explícita a la pregunta de la introducción**) · 10. Contribuciones por integrante + declaración de uso de IA generativa + reflexión de media página · 11. Referencias en formato IEEE.

Toda cifra, tabla y figura debe provenir de `experiments/`. **Las referencias deben ser reales y verificables.**

---

## 15. Sustentación (20 min, nota individual)

- Cada integrante responde preguntas conceptuales (p. ej. «¿por qué F1 y no exactitud?», «¿por qué esta partición?», «¿qué pasaría con el sobreajuste si…?») y hace **una modificación pequeña en vivo** (hiperparámetro, regla o umbral) **prediciendo el efecto antes de ejecutar**.
- Un integrante que no pueda explicar su contribución declarada recibe nota individual inferior.
- **Implicación para Copilot:** escribe código que el equipo pueda explicar; justifica en 2–3 líneas cada decisión de modelado enlazándola a un concepto del curso (capítulo del libro guía o artículo); evita abstracciones innecesarias.

---

## 16. Cómo debe comportarse Copilot en este repositorio

**Hacer**
- Leer §1 antes de proponer código; mantener coherencia con métrica, partición y línea base declaradas.
- Hacer cambios pequeños e incrementales; **ejecutar antes de afirmar que funciona** y reportar qué se ejecutó y qué salió.
- Señalar proactivamente riesgos de fuga de datos, desbalance, deriva temporal y subgrupos desatendidos.
- Advertir cuando un pedido choque con la rúbrica o con las reglas de §3.
- Sugerir la entrada de bitácora (§13) tras contribuciones sustantivas.
- Preferir `pandas` + `scikit-learn` + librerías ligeras que corran en equipo personal, Colab o Kaggle.

**No hacer**
- No cambiar métrica, umbral ni partición sin dejar registro en §19.
- No usar el conjunto de prueba para decidir nada.
- No inventar resultados, errores de ejemplo, referencias, endpoints ni campos de API.
- No agregar herramientas, carpetas o dependencias que el proyecto no necesite.
- No subir datos personales, llaves ni archivos pesados.
- No dejar la solución final solo en un notebook.

---

## 17. Comandos

No hay comandos definidos todavía. **Solo documentar y usar comandos que existan.** Meta del README (menos de 5 comandos; los nombres cambiarán, actualizar esta tabla cuando se implementen):

| Propósito | Comando | Existe |
|---|---|---|
| Entorno e instalación | `python -m venv .venv` + `pip install -r requirements.txt` | ☐ |
| Descargar/actualizar datos crudos | `python -m src.data.<script>` | ☐ |
| Ejecutar línea base + modelos | `python -m src.models.<script>` | ☐ |
| Lanzar el prototipo | `streamlit run app/<archivo>.py` (o equivalente) | ☐ |
| Pruebas (si se agregan) | `python -m pytest` · una sola: `python -m pytest ruta/test_x.py -k nombre` | ☐ |

---

## 18. Rúbrica de bolsillo (100 pts)

| # | Criterio | Pts | Para «Excelente» |
|---|---|---|---|
| 1 | Problema y formulación | 10 | Problema real con evidencia; PEAS y tarea formal completos |
| 2 | Datos o conocimiento | 10 | Fuente, licencia, preprocesamiento y partición justificados; **sin fuga** |
| 3 | Fundamento y justificación técnica | 10 | Elección argumentada con libro guía y artículos; alternativas discutidas |
| 4 | Implementación y reproducibilidad | 15 | Se ejecuta siguiendo el README; resultados replicables; commits distribuidos |
| 5 | Experimentación y evaluación | 15 | Línea base + comparación mínima; métricas predeclaradas; **varias corridas o validación cruzada** |
| 6 | Análisis crítico de resultados | 10 | ≥10 errores clasificados con hipótesis; conclusiones ≤ evidencia |
| 7 | IA responsable | 10 | Riesgos específicos, medidos (p. ej. por subgrupo), con mitigaciones |
| 8 | Comunicación escrita y bitácora IA | 5 | Informe IEEE claro; bitácora completa con verificación y reflexión |
| 9 | Sustentación (individual) | 15 | Respuestas precisas y predicción correcta de la modificación en vivo |

Si falta uno de los nueve componentes obligatorios, su criterio no puede superar «Insuficiente».

---

## 19. Registro de decisiones y cambios

Anotar aquí cada decisión relevante, y **obligatoriamente** cualquier cambio de métrica, umbral o partición posterior al Hito 1, con justificación escrita.

| Fecha | Decisión o cambio | Justificación | Quién |
|---|---|---|---|
| 2026-11-05 | Se elige la Ruta C (Aprendizaje automático) con dataset crudo construido desde APIs gratuitas | Decisión del equipo | |
| 2026-11-05 | Dominio: energía — precio de bolsa de la electricidad (XM + clima) | Camino distinto al ejemplo agro del enunciado; datos públicos, sin datos personales, API verificada | |
| 2026-11-05 | Hito 1 redactado: objetivo t+1, partición cronológica, líneas base B0/B1/B2, MAE primaria y umbral de mejora ≥10 % | Declarado antes de experimentar | |
