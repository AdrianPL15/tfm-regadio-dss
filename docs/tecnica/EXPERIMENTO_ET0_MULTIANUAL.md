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

Se obtuvieron series diarias de tres estaciones entre el 1 de enero de 2021 y
el 31 de diciembre de 2025:

- AL01 (La Mojonera): 1.826 fechas y 34 valores ausentes de ET0;
- Z06 (Ejea de los Caballeros): 1.826 fechas y 72 valores ausentes de ET0;
- BA08 (Don Benito): 1.826 fechas y ningún valor ausente de ET0;
- las tres series presentan cobertura completa del calendario;
- temperatura, humedad, radiación, viento y precipitación como variables
  meteorológicas auxiliares;
- los ficheros originales se conservan en `data/raw/siar/public_history/`, ruta
  excluida del control de versiones por tratarse de datos regenerables;
- el inventario y el resumen de calidad quedan trazados en
  `docs/data_samples/et0_history_inventory.*` y
  `docs/data_samples/et0_history_quality_<ESTACION>_2021_2025.csv`.

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

## Validación geográfica sin reajuste

El protocolo definido con AL01 se congeló y se repitió sin cambiar variables,
modelos, hiperparámetros, particiones ni semilla en Z06 y BA08. Ridge volvió a
ser seleccionado mediante la validación temporal de 2021–2024 y superó a la
persistencia en el año externo 2025 en las tres estaciones:

| Estación | Cultivo de impacto | Días ET0 comparables | MAE Ridge | MAE persistencia | Mejora relativa |
|---|---|---:|---:|---:|---:|
| AL01 | Pimiento | 357 | 0,389 | 0,463 | 16,1 % |
| Z06 | Maíz | 293 | 0,558 | 0,688 | 18,9 % |
| BA08 | Algodón | 365 | 0,403 | 0,466 | 13,7 % |

Los 293 días comparables de Z06 se explican por la ausencia de ET0 en 72 fechas,
no por una selección favorable posterior. La evidencia consolidada se conserva
en `docs/data_samples/et0_multiyear_geographic_validation.csv`.

## Incertidumbre estadística

Se aplicó un bootstrap pareado por bloques temporales circulares de siete días,
con 5.000 réplicas y semilla 42. El estimando es `MAE de persistencia − MAE del
modelo`; un resultado positivo favorece al modelo.

Los intervalos del 95 % de la diferencia `MAE persistencia − MAE Ridge` fueron
[0,049; 0,103] mm/día en AL01, [0,075; 0,185] en Z06 y [0,036; 0,092] en BA08.
La proporción de réplicas positivas fue 1,000 en las tres estaciones. Ningún
intervalo cruza cero dentro de 2025; la mejora es consistente geográficamente
en este conjunto, aunque todavía no acredita estabilidad en otros años futuros.

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

Ridge reduce el MAE diario de necesidad neta frente a persistencia un 18,6 % en
pimiento/AL01, un 23,3 % en maíz/Z06 y un 18,2 % en algodón/BA08. El interés no
está en el parecido acumulado aislado —los errores positivos y negativos pueden
compensarse—, sino en la reducción del error diario. En todos los casos se usó
Pe observada únicamente para esta evaluación retrospectiva.

## Limitaciones y decisión provisional

El experimento aporta evidencia favorable y transferible entre las tres zonas,
pero todavía procede mantenerlo separado de la entrega estable:

1. solo se ha evaluado un año externo completo (2025);
2. las tres estaciones no representan toda la diversidad agroclimática española;
3. las variables meteorológicas observadas del día anterior no equivalen a
   integrar previsiones meteorológicas futuras completas;
4. la evaluación con precipitación observada aísla el efecto de ET0, pero no
   valida el error real de la API de AEMET;
5. faltaría definir el artefacto de modelo, su actualización y el comportamiento
   de respaldo si la predicción no está disponible.

La decisión provisional pasa a ser **candidato favorable a integración
controlada**, no integración automática. Antes de sustituir a la persistencia
en la aplicación debe serializarse y versionarse el modelo, definir el respaldo
cuando falten variables, comparar su entrada operativa con la disponibilidad
real de AEMET y ejecutar una prueba de regresión completa de Streamlit. Hasta
entonces la persistencia continúa siendo el comportamiento estable del DSS.

## Preparación técnica para una integración controlada

Se ha preparado una capa experimental que todavía no está conectada a
Streamlit. Tras congelar la evaluación externa de 2025, Ridge se reajusta con
todo el histórico 2021–2025 de cada estación. Los tres artefactos se conservan
en `models/experimental_et0_multiyear/` junto a un manifiesto que declara:

- estación, periodo y número de filas de entrenamiento;
- orden exacto de las variables de entrada;
- MAE de Ridge y persistencia medidos antes del reajuste, sobre 2025;
- nombre y huella SHA-256 del artefacto;
- estado explícito `experimental_not_deployed`.

La inferencia de `src/dss/predict_et0.py` solo intenta Ridge cuando existe una
observación del día inmediatamente anterior y al menos tres retardos de ET0
válidos. Verifica la huella del artefacto y no utiliza registros de la fecha
objetivo ni posteriores. Ante un modelo ausente, manipulado, una estación no
registrada, datos desactualizados o histórico insuficiente, devuelve de forma
trazable la persistencia de la última ET0 observada. Si tampoco existe esa ET0,
declara el resultado como no disponible.

Una comprobación de inferencia para el 1 de enero de 2026 produjo Ridge en AL01
y BA08, mientras Z06 activó correctamente el respaldo por falta de suficientes
retardos recientes. Este comportamiento confirma que el respaldo no es solo
una especificación documental. La siguiente fase, todavía pendiente, es
construir una tabla operativa diaria con las mismas variables desde SiAR y
decidir qué campos futuros de AEMET pueden incorporarse sin cambiar el contrato
validado.

## Auditoría de preparación operativa

La auditoría `src/analysis/audit_et0_operational_readiness.py` confirma que la
entrada actual de Streamlit no satisface aún el contrato de Ridge. Los CSV de
necesidades hídricas aportan fecha, Kc, ET0, ETc, Pe y necesidad neta, pero no
incluyen las series completas de temperatura, humedad, viento, radiación y
precipitación observada que utilizó el experimento. Imputar columnas enteras
supondría un escenario diferente al evaluado y podría degradar el resultado sin
que las métricas de 2025 lo reflejasen; por ello la inferencia lo rechaza y
activa persistencia.

AEMET tampoco debe rellenar esas columnas: el producto municipal disponible
aporta lluvia prevista y su probabilidad, no las observaciones SiAR de la
estación en `t-1`. Su papel permanece separado y correcto: descontar una sola
vez la lluvia prevista después de obtener `ETc = ET0 × Kc`.

Se implementó después un adaptador de la API SiAR que normaliza las
observaciones diarias al esquema del entrenamiento. La prueba real realizada
el 29 de octubre de 2026 sobre AL01 recuperó 29 registros, todos con ET0 y
calidad `PASS`, pero la última observación disponible correspondía al 27 de
octubre. Para recomendar el día 29 habría que proyectar dos pasos y el
experimento solo ha validado un paso. El sistema activó correctamente
persistencia en vez de extrapolar fuera de su alcance.

El estado de integración queda como
`blocked_siar_publication_lag_for_same_day`. La barrera de columnas está
resuelta, pero debe medirse la latencia habitual de SiAR y, si el desfase de dos
días es recurrente, evaluar de forma separada un modelo a horizonte dos antes
de desplegarlo. AEMET no publica ET0 y no corrige por sí sola este desfase. El
informe de preparación se guarda en
`docs/data_samples/et0_operational_readiness.json` y la evidencia de la prueba
real en `docs/data_samples/et0_live_siar_smoke_2026-10-29.json`.

## Artefactos generados

- `src/analysis/audit_et0_availability.py`: inventario de fuentes disponibles;
- `src/data/prepare_et0_history.py`: normalización y control de calidad;
- `src/models/train_et0_multiyear.py`: entrenamiento y validación temporal;
- `src/analysis/evaluate_et0_multiyear.py`: bootstrap e impacto agronómico;
- `src/models/export_et0_multiyear.py`: reajuste y versionado experimental;
- `src/dss/predict_et0.py`: inferencia con verificación y respaldo;
- `src/analysis/audit_et0_operational_readiness.py`: compatibilidad entre el
  contrato del modelo y las fuentes que alimentan actualmente Streamlit;
- `docs/data_samples/et0_multiyear_metrics.csv`: métricas de modelos;
- `docs/data_samples/et0_multiyear_predictions_2025.csv`: predicciones de prueba;
- `docs/data_samples/et0_multiyear_statistical_evidence.csv`: incertidumbre;
- `docs/data_samples/et0_multiyear_irrigation_impact.csv`: efecto en el riego;
- `docs/data_samples/et0_multiyear_evaluation_summary.json`: síntesis auditable.
- `docs/data_samples/et0_multiyear_*_Z06.*` y `*_BA08.*`: réplica geográfica;
- `docs/data_samples/et0_multiyear_geographic_validation.csv`: comparación
  consolidada de las tres estaciones.

Las pruebas automatizadas comprueban la construcción de objetivo a un día, la
ausencia de fuga temporal, la calidad del calendario, la reproducibilidad del
bootstrap y la aplicación única de Kc y precipitación.
