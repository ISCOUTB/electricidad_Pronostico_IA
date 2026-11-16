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
