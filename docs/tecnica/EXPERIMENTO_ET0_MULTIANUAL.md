# Experimento aislado de predicción multianual de ET0

## Alcance y separación de la entrega

Este trabajo se desarrolla en `codex/experimento-et0-multianual` y no modifica
la versión estable del TFM, la memoria ni la aplicación Streamlit. Su objetivo
es comprobar si una predicción de ET0 del día siguiente mejora la referencia de
persistencia antes de decidir si merece incorporarse al DSS.

La ET0 es una variable meteorológica asociada a la estación, no al cultivo. La
transformación agronómica se realiza después mediante `ETc = ET0 × Kc`. En el
funcionamiento operativo futuro, la precipitación útil prevista por AEMET se
descontaría una sola vez para obtener la necesidad neta.

## Adquisición y calidad de datos

El token actual de la API de SiAR solo autoriza fechas desde el 1 de mayo de
2025. Para no entrenar con una muestra corta, el histórico se descargó desde la
consulta pública oficial de SiAR, que permite recuperar años anteriores en
bloques de hasta 365 registros.

Se obtuvo la serie diaria de la estación AL01 (La Mojonera) entre el 1 de enero
de 2021 y el 31 de diciembre de 2025:

- 1.826 fechas, con cobertura completa del calendario;
- 34 valores ausentes de ET0: 29 en 2022 y 5 en 2025;
- temperatura, humedad, radiación, viento y precipitación como variables
  meteorológicas auxiliares;
- los ficheros originales se conservan en `data/raw/siar/public_history/`, ruta
  excluida del control de versiones por tratarse de datos regenerables;
- el inventario y el resumen de calidad quedan trazados en
  `docs/data_samples/et0_history_inventory.*` y
  `docs/data_samples/et0_history_quality_AL01_2021_2025.csv`.

La normalización reproducible se ejecuta con:

```text
python -m src.data.prepare_et0_history
```

## Diseño experimental

El objetivo es la ET0 del día siguiente en mm/día. Las variables se construyen
solo con información anterior a la fecha objetivo:

- retardos de ET0 de 1, 2, 3, 7 y 14 días;
- medias móviles de ET0 de 3, 7 y 14 días;
- temperatura, humedad, radiación, viento y precipitación del día anterior;
- codificación cíclica del día del año.

Se utilizaron 2021–2024 para desarrollo, con cuatro particiones temporales
progresivas (`TimeSeriesSplit`), y todo 2025 como prueba externa temporal. Los
modelos candidatos fueron Ridge, Random Forest, HistGradientBoosting y XGBoost.
Las referencias simples fueron persistencia, media móvil de siete días y
climatología por día del año calculada solo con el periodo de desarrollo. La
selección se realizó mediante MAE medio de validación, no observando el año de
prueba. La semilla común es 42.

El entrenamiento se reproduce con:

```text
python -m src.models.train_et0_multiyear
```

## Resultados de ET0 en 2025

Ridge fue seleccionado en validación y también obtuvo el menor error sobre los
357 días comparables de 2025:

| Método | MAE (mm/día) | RMSE (mm/día) | R² |
|---|---:|---:|---:|
| Ridge | 0,389 | 0,557 | 0,903 |
| Random Forest | 0,420 | 0,584 | 0,893 |
| XGBoost | 0,428 | 0,590 | 0,891 |
| HistGradientBoosting | 0,429 | 0,585 | 0,893 |
| Persistencia | 0,463 | 0,670 | 0,860 |
| Media móvil 7 días | 0,481 | 0,690 | 0,851 |
| Climatología | 0,519 | 0,707 | 0,844 |

La mejora puntual de Ridge frente a persistencia fue de 0,074 mm/día, un
16,1 % del MAE de la referencia.

## Incertidumbre estadística

Se aplicó un bootstrap pareado por bloques temporales circulares de siete días,
con 5.000 réplicas y semilla 42. El estimando es `MAE de persistencia − MAE del
modelo`; un resultado positivo favorece al modelo.

Para Ridge, la diferencia fue 0,074 mm/día, con IC del 95 % de 0,049 a 0,103
mm/día y una proporción de réplicas positivas de 1,000. El intervalo no cruza
cero dentro de esta campaña, por lo que la mejora no parece explicarse solo por
la variación muestral interna de 2025. Esta inferencia no acredita transferencia
a otras estaciones ni años.

La evaluación se reproduce con:

```text
python -m src.analysis.evaluate_et0_multiyear
```

## Traducción a la recomendación de riego

Para comprobar la utilidad agronómica se alinearon las predicciones de ET0 con
145 días del ciclo 2025 de pimiento en AL01. Se aplicó el Kc diario de SiAR y,
solo para esta evaluación retrospectiva, la precipitación efectiva observada.
No se utilizó esa precipitación para entrenar el modelo ni se presenta como una
validación de la previsión operativa de AEMET.

| Método | MAE ETc (mm/día) | MAE necesidad neta (mm/día) | Necesidad acumulada (mm) |
|---|---:|---:|---:|
| Persistencia | 0,326 | 0,322 | 516,945 |
| Ridge | 0,266 | 0,262 | 515,791 |
| Referencia SiAR | — | — | 515,840 |

Ridge reduce el MAE diario de necesidad neta un 18,6 % frente a persistencia y
su acumulado queda muy próximo al de SiAR. El interés no está en ese parecido
acumulado aislado —los errores positivos y negativos pueden compensarse—, sino
en la reducción del error diario.

## Limitaciones y decisión provisional

El experimento aporta evidencia favorable, pero todavía procede mantenerlo
separado de la entrega estable:

1. solo se ha evaluado una estación (AL01) y un año de prueba;
2. el impacto agronómico solo se ha contrastado con el ciclo del pimiento;
3. las variables meteorológicas observadas del día anterior no equivalen a
   integrar previsiones meteorológicas futuras completas;
4. la evaluación con precipitación observada aísla el efecto de ET0, pero no
   valida el error real de la API de AEMET;
5. faltaría definir el artefacto de modelo, su actualización y el comportamiento
   de respaldo si la predicción no está disponible.

La decisión provisional es **continuar la validación geográfica antes de
integrar**. El siguiente hito recomendable es repetir el protocolo con Z06 y
BA08 —sin ajustar el método al resultado de AL01— y decidir después si Ridge
debe sustituir a la persistencia en la aplicación o quedar como experimento.

## Artefactos generados

- `src/analysis/audit_et0_availability.py`: inventario de fuentes disponibles;
- `src/data/prepare_et0_history.py`: normalización y control de calidad;
- `src/models/train_et0_multiyear.py`: entrenamiento y validación temporal;
- `src/analysis/evaluate_et0_multiyear.py`: bootstrap e impacto agronómico;
- `docs/data_samples/et0_multiyear_metrics.csv`: métricas de modelos;
- `docs/data_samples/et0_multiyear_predictions_2025.csv`: predicciones de prueba;
- `docs/data_samples/et0_multiyear_statistical_evidence.csv`: incertidumbre;
- `docs/data_samples/et0_multiyear_irrigation_impact.csv`: efecto en el riego;
- `docs/data_samples/et0_multiyear_evaluation_summary.json`: síntesis auditable.

Las pruebas automatizadas comprueban la construcción de objetivo a un día, la
ausencia de fuga temporal, la calidad del calendario, la reproducibilidad del
bootstrap y la aplicación única de Kc y precipitación.
