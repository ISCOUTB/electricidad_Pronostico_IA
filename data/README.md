# Datos del proyecto

## Clima histórico

Fuente: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), datos de reanálisis ERA5 solicitados desde el 2015-01-01. ERA5 es un reanálisis y no una observación directa de cada punto. Los días se solicitan en la zona horaria `America/Bogota` (UTC−5) para alinearlos con las fechas diarias de XM.

Variables diarias devueltas por la API:

| Campo API | Descripción | Unidad |
|---|---|---|
| `temperature_2m_mean` | Temperatura media a 2 m | °C |
| `temperature_2m_max` | Temperatura máxima a 2 m | °C |
| `precipitation_sum` | Precipitación acumulada diaria | mm |

Licencia: **CC BY 4.0**. Atribución requerida: **Weather data by Open-Meteo.com**.

Puntos consultados (coordenadas aproximadas suministradas para el proyecto):

| Punto | Latitud | Longitud |
|---|---:|---:|
| Barranquilla | 10.96 | -74.80 |
| Bogotá | 4.71 | -74.07 |
| Medellín | 6.25 | -75.56 |
| Cali | 3.45 | -76.53 |
| Guatapé / El Peñol | 6.20 | -75.20 |
| Guavio | 4.80 | -73.50 |

Las respuestas originales y sus metadatos se guardan por punto en `data/raw/openmeteo/`. El endpoint puede devolver fechas recientes con valores nulos mientras se publican los datos ERA5; el rango con datos válidos y los faltantes al final se informan al ejecutar `src/data/download_openmeteo.py`.

## Series diarias de XM

Fuente: API XM (Sinergox), consultada con el catálogo de `pydataxm` y solicitudes al endpoint diario. Descarga iniciada el **2026-11-16**. Las respuestas crudas se guardan por métrica y ventana de hasta 30 días en `data/raw/xm/<MetricId>/`, junto con metadatos por respuesta.

| MetricId | Métrica del catálogo XM | Granularidad | Entidad | Unidad |
|---|---|---|---|---|
| `PPPrecBolsNaci` | Precio Bolsa Nacional Ponderado por Sistema | Diaria | Sistema | COP/kWh |
| `DemaSIN` | Demanda Energía SIN por Sistema | Diaria | Sistema | kWh |
| `AporEner` | Aportes Energía por Sistema | Diaria | Sistema | kWh |
| `AporEnerMediHist` | Aportes Media Histórica Energía por Sistema | Diaria | Sistema | kWh |
| `VoluUtilDiarEner` | Volumen Útil diario Energía por Sistema | Diaria | Sistema | kWh |

Periodo solicitado: **2015-01-01 a 2026-11-09**. La fecha final común, `data_cutoff`, está centralizada en `config/config.yaml`; los descargadores del proyecto la consultan para mantener alineados los periodos.

Uso citando la fuente XM (confirmado por el equipo, 2026-11-16). Atribución: fuente XM.

## Dataset de modelado

`data/interim/daily_wide.csv` contiene las 23 series fuente alineadas por fecha, sin variables derivadas. `data/processed/{train,val,test}.csv` contiene las variables construidas hasta el día `t`, el objetivo `y_next = PPPrecBolsNaci(t+1)`, `target_date` y columnas auxiliares. La ventana móvil incluye el día `t`; las filas sin 30 días completos y el último día sin objetivo se descartan. Las particiones se asignan por `target_date`. Los límites de terciles de aportes/media se ajustan solo con train.

### Diccionario de variables

| Variable | Descripción | Unidad | Fuente | Grupo |
|---|---|---|---|---|
| `price_t` | Precio oficial ponderado en t | COP/kWh | XM `PPPrecBolsNaci` | price |
| `price_lag_1` | Precio de t−1 | COP/kWh | XM `PPPrecBolsNaci` | price |
| `price_lag_2` | Precio de t−2 | COP/kWh | XM `PPPrecBolsNaci` | price |
| `price_lag_3` | Precio de t−3 | COP/kWh | XM `PPPrecBolsNaci` | price |
| `price_lag_6` | Precio de t−6 | COP/kWh | XM `PPPrecBolsNaci` | price |
| `price_mean_7d` | Media de precios de t y seis días previos | COP/kWh | XM `PPPrecBolsNaci` | price |
| `price_mean_14d` | Media de precios de t y trece días previos | COP/kWh | XM `PPPrecBolsNaci` | price |
| `price_mean_30d` | Media de precios de t y 29 días previos | COP/kWh | XM `PPPrecBolsNaci` | price |
| `price_std_7d` | Desviación estándar de precios de t y seis días previos | COP/kWh | XM `PPPrecBolsNaci` | price |
| `price_std_30d` | Desviación estándar de precios de t y 29 días previos | COP/kWh | XM `PPPrecBolsNaci` | price |
| `price_max_30d` | Máximo precio de t y 29 días previos | COP/kWh | XM `PPPrecBolsNaci` | price |
| `demand_t` | Demanda de energía del SIN en t | kWh | XM `DemaSIN` | demand |
| `demand_mean_7d` | Media de demanda de t y seis días previos | kWh | XM `DemaSIN` | demand |
| `target_day_of_week` | Día de semana de target_date (lunes=0, domingo=6) | día (0–6) | Calendario | calendar |
| `target_is_non_working` | Si target_date es fin de semana o festivo colombiano | booleano | Calendario, `holidays` | calendar |
| `target_month` | Mes de target_date | mes (1–12) | Calendario | calendar |
| `aportes_t` | Aportes energéticos en t | kWh | XM `AporEner` | hydro |
| `aportes_media_hist_t` | Media histórica de aportes en t | kWh | XM `AporEnerMediHist` | hydro |
| `aportes_ratio_t` | Aportes divididos por media histórica en t | razón | XM `AporEner` / `AporEnerMediHist` | hydro |
| `aportes_ratio_mean_7d` | Media de la razón en t y seis días previos | razón | XM `AporEner` / `AporEnerMediHist` | hydro |
| `aportes_ratio_mean_30d` | Media de la razón en t y 29 días previos | razón | XM `AporEner` / `AporEnerMediHist` | hydro |
| `volumen_util_t` | Volumen útil de embalses en t | kWh | XM `VoluUtilDiarEner` | hydro |
| `volumen_util_change_7d` | Cambio de volumen útil entre t y t−7 | kWh | XM `VoluUtilDiarEner` | hydro |
| `climate_barranquilla_temperature_mean_t` | Temperatura media en t | °C | Open-Meteo ERA5, Barranquilla | climate |
| `climate_barranquilla_temperature_max_t` | Temperatura máxima en t | °C | Open-Meteo ERA5, Barranquilla | climate |
| `climate_barranquilla_precipitation_t` | Precipitación en t | mm | Open-Meteo ERA5, Barranquilla | climate |
| `climate_barranquilla_precipitation_sum_7d` | Precipitación acumulada de t y seis días previos | mm | Open-Meteo ERA5, Barranquilla | climate |
| `climate_barranquilla_precipitation_sum_30d` | Precipitación acumulada de t y 29 días previos | mm | Open-Meteo ERA5, Barranquilla | climate |
| `climate_bogota_temperature_mean_t` | Temperatura media en t | °C | Open-Meteo ERA5, Bogotá | climate |
| `climate_bogota_temperature_max_t` | Temperatura máxima en t | °C | Open-Meteo ERA5, Bogotá | climate |
| `climate_bogota_precipitation_t` | Precipitación en t | mm | Open-Meteo ERA5, Bogotá | climate |
| `climate_bogota_precipitation_sum_7d` | Precipitación acumulada de t y seis días previos | mm | Open-Meteo ERA5, Bogotá | climate |
| `climate_bogota_precipitation_sum_30d` | Precipitación acumulada de t y 29 días previos | mm | Open-Meteo ERA5, Bogotá | climate |
| `climate_medellin_temperature_mean_t` | Temperatura media en t | °C | Open-Meteo ERA5, Medellín | climate |
| `climate_medellin_temperature_max_t` | Temperatura máxima en t | °C | Open-Meteo ERA5, Medellín | climate |
| `climate_medellin_precipitation_t` | Precipitación en t | mm | Open-Meteo ERA5, Medellín | climate |
| `climate_medellin_precipitation_sum_7d` | Precipitación acumulada de t y seis días previos | mm | Open-Meteo ERA5, Medellín | climate |
| `climate_medellin_precipitation_sum_30d` | Precipitación acumulada de t y 29 días previos | mm | Open-Meteo ERA5, Medellín | climate |
| `climate_cali_temperature_mean_t` | Temperatura media en t | °C | Open-Meteo ERA5, Cali | climate |
| `climate_cali_temperature_max_t` | Temperatura máxima en t | °C | Open-Meteo ERA5, Cali | climate |
| `climate_cali_precipitation_t` | Precipitación en t | mm | Open-Meteo ERA5, Cali | climate |
| `climate_cali_precipitation_sum_7d` | Precipitación acumulada de t y seis días previos | mm | Open-Meteo ERA5, Cali | climate |
| `climate_cali_precipitation_sum_30d` | Precipitación acumulada de t y 29 días previos | mm | Open-Meteo ERA5, Cali | climate |
| `climate_guatape_el_penol_temperature_mean_t` | Temperatura media en t | °C | Open-Meteo ERA5, Guatapé / El Peñol | climate |
| `climate_guatape_el_penol_temperature_max_t` | Temperatura máxima en t | °C | Open-Meteo ERA5, Guatapé / El Peñol | climate |
| `climate_guatape_el_penol_precipitation_t` | Precipitación en t | mm | Open-Meteo ERA5, Guatapé / El Peñol | climate |
| `climate_guatape_el_penol_precipitation_sum_7d` | Precipitación acumulada de t y seis días previos | mm | Open-Meteo ERA5, Guatapé / El Peñol | climate |
| `climate_guatape_el_penol_precipitation_sum_30d` | Precipitación acumulada de t y 29 días previos | mm | Open-Meteo ERA5, Guatapé / El Peñol | climate |
| `climate_guavio_temperature_mean_t` | Temperatura media en t | °C | Open-Meteo ERA5, Guavio | climate |
| `climate_guavio_temperature_max_t` | Temperatura máxima en t | °C | Open-Meteo ERA5, Guavio | climate |
| `climate_guavio_precipitation_t` | Precipitación en t | mm | Open-Meteo ERA5, Guavio | climate |
| `climate_guavio_precipitation_sum_7d` | Precipitación acumulada de t y seis días previos | mm | Open-Meteo ERA5, Guavio | climate |
| `climate_guavio_precipitation_sum_30d` | Precipitación acumulada de t y 29 días previos | mm | Open-Meteo ERA5, Guavio | climate |

`y_next` es la etiqueta `PPPrecBolsNaci` en `target_date` (t+1), unidad COP/kWh; no es una variable de entrada. `hydro_regime`, `tipo_dia` y `year` son columnas auxiliares y tampoco son variables del modelo. Los cortes de `hydro_regime` provienen únicamente de train. El paquete `holidays==0.108` (MIT) soporta Colombia; reconoce el 2026-01-01 y el 2026-12-25 como festivos.

| Variable | Descripción | Unidad | Fuente | Grupo |
|---|---|---|---|---|
| `date` | Fecha de observación de las entradas (t) | fecha | XM / Open-Meteo | índice |
| `target_date` | Fecha del objetivo (t+1) | fecha | Calendario diario | etiqueta auxiliar |
| `y_next` | Precio oficial ponderado en target_date | COP/kWh | XM `PPPrecBolsNaci` | objetivo |
| `hydro_regime` | Tercil bajo/medio/alto de aportes/media en t; cortes ajustados solo con train | categoría | XM `AporEner` / `AporEnerMediHist` | auxiliar |
| `tipo_dia` | Hábil o no laboral en target_date | categoría | Calendario, `holidays` | auxiliar |
| `year` | Año de target_date | año | Calendario diario | auxiliar |

### Resumen del objetivo por conjunto

Estadísticos de `y_next` en COP/kWh; la fecha del máximo corresponde a `target_date`.

| Conjunto | n | Media | Mediana | Máximo | Fecha del máximo |
|---|---:|---:|---:|---:|---|
| train | 2892 | 221.23 | 160.58 | 1942.71 | 2015-10-08 |
| val | 731 | 624.08 | 556.09 | 2498.80 | 2024-09-30 |
| test | 678 | 360.40 | 265.69 | 1031.88 | 2026-08-05 |

### Resumen anual del objetivo

| Año | n | Media | Mediana | Máximo | Fecha del máximo |
|---:|---:|---:|---:|---:|---|
| 2015 | 335 | 399.60 | 220.25 | 1942.71 | 2015-10-08 |
| 2016 | 366 | 303.21 | 177.73 | 884.37 | 2016-03-10 |
| 2017 | 365 | 107.54 | 107.51 | 200.08 | 2017-02-14 |
| 2018 | 365 | 117.75 | 109.70 | 348.04 | 2018-12-31 |
| 2019 | 365 | 232.05 | 231.37 | 422.51 | 2019-10-09 |
| 2020 | 366 | 254.38 | 224.21 | 607.74 | 2020-02-21 |
| 2021 | 365 | 151.35 | 111.20 | 584.95 | 2021-12-21 |
| 2022 | 365 | 218.29 | 199.59 | 685.50 | 2022-02-03 |
| 2023 | 365 | 564.48 | 515.04 | 1482.24 | 2023-10-24 |
| 2024 | 366 | 683.52 | 582.71 | 2498.80 | 2024-09-30 |
| 2025 | 365 | 245.16 | 209.56 | 765.95 | 2025-01-29 |
| 2026 | 313 | 494.78 | 454.01 | 1031.88 | 2026-08-05 |

### Limitaciones y calidad temporal

- ERA5 es reanálisis de aproximadamente 25 km de resolución; no representa observaciones puntuales de cada ciudad o embalse.
- La publicación de XM presenta un rezago cercano a 7 días respecto al corte disponible. Los datos recientes pueden revisarse y las últimas ventanas deben reconsultarse antes de fijar una versión definitiva.
- Las filas iniciales se descartan hasta completar la ventana retrospectiva de 30 días; también se descarta la fecha final si no existe `y_next` dentro del corte.
- La comparación exploratoria de `DemaSIN` y la suma horaria de `DemaReal` mostró diferencias; el proyecto conserva `DemaSIN` como entrada diaria definida por el equipo, sin sustituirla por la demanda horaria.
