# Reproducción independiente del piloto

Este repositorio conserva una excepción pequeña y explícita a la exclusión de
datos `raw`: tres respuestas públicas de SiAR/AEMET utilizadas en la memoria.
Junto con el CSV oficial de necesidades de cultivo ya versionado, permiten
reconstruir la ETL, la tabla analítica, la comparación de modelos y la
validación del DSS sin utilizar tokens. No contienen claves, datos de parcelas
ni información personal. Los demás archivos de `data/raw`, `data/interim` y
`data/processed` permanecen excluidos del control de versiones.

## Entradas congeladas

| Entrada | Periodo | SHA-256 |
|---|---|---|
| `data/raw/siar/weather/daily/station=AL01/period=2025-05-01_2025-09-30/history__20260924T113344Z.json` | 150 fechas observadas, mayo-septiembre de 2025 | `96964733D9F81BD8440C8ADB84201519E69222D6540E01A1FA8E4F37F446FDCD` |
| `data/external/siar_necesidades_pimiento_AL01_2025.csv` | 150 filas de necesidades; estación AL01, cultivo Pimiento | `626612EF2A396F3C47AF3729B991B57F900C54BAE697FC94C6E5809210047BD1` |
| `data/raw/aemet/forecast/daily/municipality=04013/ingestion_date=2026-09-24/20260924T085620Z.json` | Predicción municipal de ejemplo, septiembre de 2026 | `84C41116C08B1478F8640BACA6C1256A343797E68501497D74258E071F51D95D` |
| `data/raw/aemet/forecast/hourly/municipality=04013/ingestion_date=2026-09-24/20260924T085620Z.json` | Predicción horaria municipal de ejemplo, septiembre de 2026 | `5C83FBA3C38F7B45A033D21F6B0F198B4BC49E80CEB872548DF28B27D8449325` |

Las respuestas AEMET no se usan como predictores del modelo: fueron emitidas
en 2026 y no corresponden a la campaña SiAR de 2025. Solo demuestran que el
conector y la normalización funcionan. Las fechas de descarga y los parámetros
de consulta se conservan en los sobres JSON y en
`data/external/siar_necesidades_pimiento_AL01_2025.metadata.json`.

## Comandos desde un clon limpio

Crear un entorno virtual e instalar `requirements-piloto.txt`, que fija las
versiones principales comprobadas localmente. Después, desde la
raíz del repositorio, ejecutar:

```powershell
python -m src.data.transform_interim
python -m src.features.feature_engineering
python -m src.analysis.build_etl_audit_4_1
python -m src.analysis.build_eda_4_2
python -m src.models.train_evaluate
python -m src.analysis.build_xai_4_3
python -m src.analysis.build_validation_5_3
python -m unittest discover -s tests -q
streamlit run src/dss/app_streamlit.py
```

En este clon hay un único raw meteorológico SiAR y un único CSV de cultivo;
por eso la selección automática es inequívoca. Si se añaden campañas o
cultivos, indicar expresamente `--siar-weather-file` y `--crop-needs-file` al
primer comando. El programa comprueba que coincidan estación y fechas.

La reproducción desde una copia compuesta solo por archivos versionados se
comprobó de nuevo el 25/10/2026: se regeneraron ETL, tabla analítica,
comparación de modelos, análisis XAI y validación, y pasaron 104 pruebas. Las
dos pruebas de interfaz Streamlit necesitaron el entorno Windows normal porque
el aislamiento local de sockets impide que `AppTest` cargue la aplicación.

Las métricas de referencia del piloto son 150 filas meteorológicas, 150 filas
de cultivo y 148 etiquetas diarias válidas. Los resultados publicados en
`docs/data_samples` proceden de una ejecución concreta; podrían darse
diferencias numéricas pequeñas si cambian versiones de dependencias. La
evaluación mide error frente a la referencia calculada por SiAR, no eficacia
agronómica en una parcela.

## Procedencia y condiciones de reutilización

Fuente de las observaciones y necesidades: Sistema de Información
Agroclimática para el Regadío, Ministerio de Agricultura, Pesca y
Alimentación. Descarga el 24/09/2026. [Aviso legal de
SiAR](https://servicio.mapa.gob.es/siarweb/avisoLegal). La reutilización no
implica participación ni respaldo del MAPA.

Fuente de las predicciones municipales: Agencia Estatal de Meteorología
(AEMET), AEMET OpenData. Descarga el 24/09/2026. [Condiciones de
reutilización](https://www.aemet.es/es/nota_legal). Esta copia no implica
participación ni respaldo de AEMET.
