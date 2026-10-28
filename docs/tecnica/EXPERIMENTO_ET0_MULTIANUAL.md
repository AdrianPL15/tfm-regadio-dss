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

La reutilización se realiza conforme al aviso legal de SiAR. Este autoriza
expresamente usos comerciales y no comerciales, incluidas la extracción,
adaptación y combinación, con obligación de atribución y conservación de los
metadatos. La atribución aplicable es: «Fuente: Sistema de Información
Agroclimática para el Regadío. Ministerio de Agricultura, Pesca y
Alimentación». Consulta: <https://servicio.mapa.gob.es/siarweb/avisoLegal>.

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

## Ablación y comparación con la vía operativa

La aplicación estable no usa la persistencia como única referencia: su vía
física ordinaria estima `ET0 media reciente de 7 días × Kc`, mientras que la
persistencia actúa como referencia y respaldo. Por ello se añadió una
comparación sobre exactamente los mismos días con:

1. persistencia;
2. persistencia corregida por el cambio climatológico esperado entre `t` y
   `t+1`, calculado exclusivamente con los años de entrenamiento;
3. media móvil de ET0 de siete días;
4. Ridge reducido con retardos y medias de ET0 más estacionalidad;
5. Ridge completo con las variables meteorológicas auxiliares.

En 2025, Ridge completo redujo el MAE frente a la media móvil de siete días un
19,2 % en AL01, un 11,6 % en Z06 y un 20,3 % en BA08. Por tanto, la mejora no
depende de haber elegido persistencia como una referencia débil.

La ablación matiza, sin embargo, la interpretación del resultado: Ridge
completo solo superó al reducido en cinco de las nueve combinaciones
estación-año evaluadas y las diferencias fueron pequeñas. En 2025 sí lo superó
en las tres estaciones, entre un 1,7 % y un 2,7 %, pero temperatura, humedad,
viento y radiación no aportan una ganancia estable en todos los años. La mayor
parte del valor predictivo procede de la historia de ET0 y de la
estacionalidad. Este resultado evita atribuir a las variables auxiliares una
utilidad que el experimento todavía no acredita.

## Validación retrospectiva con origen rodante

Para no apoyar la conclusión en un único año, se repitió la evaluación con
ventana de entrenamiento expansiva. Cada año se predijo únicamente con años
anteriores: 2021–2022 para probar 2023, 2021–2023 para 2024 y 2021–2024 para
2025. Es una auditoría retrospectiva definida después del experimento inicial,
no tres pruebas externas independientes preespecificadas.

| Estación | Año | Días | Ridge completo | Ridge ET0 + estacionalidad | Media 7 días | Mejora frente a media 7 días |
|---|---:|---:|---:|---:|---:|---:|
| AL01 | 2023 | 365 | 0,441 | 0,441 | 0,485 | 9,0 % |
| AL01 | 2024 | 366 | 0,460 | 0,444 | 0,518 | 11,2 % |
| AL01 | 2025 | 357 | 0,389 | 0,398 | 0,481 | 19,2 % |
| Z06 | 2023 | 365 | 0,532 | 0,529 | 0,619 | 14,0 % |
| Z06 | 2024 | 366 | 0,551 | 0,555 | 0,649 | 15,0 % |
| Z06 | 2025 | 293 | 0,558 | 0,574 | 0,631 | 11,6 % |
| BA08 | 2023 | 365 | 0,486 | 0,483 | 0,548 | 11,3 % |
| BA08 | 2024 | 366 | 0,413 | 0,427 | 0,520 | 20,5 % |
| BA08 | 2025 | 365 | 0,403 | 0,410 | 0,505 | 20,3 % |

Los valores son MAE en mm/día. Ridge completo superó a la vía operativa de
siete días en las nueve comparaciones, con mejoras relativas entre el 9,0 % y
el 20,5 %. El código, el detalle completo de MAE, RMSE, R² y sesgo, y la síntesis
estructurada se conservan en `src/analysis/validate_et0_robustness.py`,
`docs/data_samples/et0_multiyear_robustness.csv` y
`docs/data_samples/et0_multiyear_robustness_summary.json`.

## Horizonte de dos días ante la latencia de SiAR

La prueba operativa del 29 de octubre mostró que la última observación SiAR
disponible era del día 27. Se repitió por ello el mismo protocolo para predecir
`t+2` desde la última observación disponible en `t`, sin reutilizar el valor
real de `t+1`. El objetivo, la fecha estacional y las particiones se desplazaron
dos días, mientras todas las entradas permanecieron en `t` o antes.

En la prueba de 2025 se obtuvieron los siguientes resultados:

| Estación | Días | Persistencia | Media 7 días | Ridge ET0 + estacionalidad | Ridge completo | Mejora frente a media 7 días |
|---|---:|---:|---:|---:|---:|---:|
| AL01 | 356 | 0,581 | 0,517 | 0,437 | 0,433 | 16,2 % |
| Z06 | 293 | 0,767 | 0,673 | 0,615 | 0,606 | 10,0 % |
| BA08 | 365 | 0,580 | 0,544 | 0,486 | 0,461 | 15,2 % |

Los valores son MAE en mm/día. La evaluación con origen rodante de 2023, 2024
y 2025 confirmó además que Ridge completo superó a la media de siete días en
las nueve combinaciones estación-año a horizonte dos. Considerando conjuntamente
los horizontes uno y dos, ganó las 18 comparaciones frente a esa referencia.
El horizonte dos queda por tanto validado como candidato experimental para
resolver el desfase observado, pero todavía no está serializado ni conectado a
la aplicación estable.

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

Los 293 días comparables de Z06 se explican por un bloque final de 72 valores
ausentes entre el 21 de octubre y el 31 de diciembre de 2025. Por tanto, su
prueba de 2025 abarca del 1 de enero al 20 de octubre; no son ausencias
aleatorias ni una selección favorable posterior. La imputación incluida en el
`Pipeline` se ajusta únicamente con el conjunto de entrenamiento, pero no se
fabrican etiquetas ET0 para esas 72 fechas. La evidencia consolidada se
conserva en `docs/data_samples/et0_multiyear_geographic_validation.csv`.

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

La réplica en los tres cultivos y zonas produjo:

| Caso | Días | MAE neto persistencia | MAE neto Ridge | Mejora | Total Ridge | Referencia SiAR |
|---|---:|---:|---:|---:|---:|---:|
| Pimiento/AL01 | 145 | 0,322 | 0,262 | 18,6 % | 515,791 | 515,840 |
| Maíz/Z06 | 183 | 0,614 | 0,471 | 23,3 % | 754,131 | 767,080 |
| Algodón/BA08 | 183 | 0,467 | 0,382 | 18,2 % | 828,763 | 834,410 |

Los errores diarios están expresados en mm/día y los acumulados en mm. El
interés no está en el parecido acumulado aislado —los errores positivos y
negativos pueden compensarse—, sino en la reducción del error diario. En todos
los casos se usó Pe observada únicamente para esta evaluación retrospectiva.
Esta mejora agronómica no constituye evidencia independiente del modelo: es la
propagación esperable del error de ET0 a través de las mismas operaciones
deterministas `ETc = ET0 × Kc` y `necesidad = max(ETc − Pe, 0)`.

## Limitaciones y decisión provisional

El experimento aporta evidencia favorable entre años y zonas, pero todavía
procede mantenerlo separado de la entrega estable:

1. 2025 es la única prueba externa originalmente preespecificada; 2023 y 2024
   son comprobaciones retrospectivas añadidas posteriormente;
2. las tres estaciones no representan toda la diversidad agroclimática española;
3. la ablación no demuestra una aportación consistente de las variables
   meteorológicas auxiliares frente a ET0 y estacionalidad;
4. las variables meteorológicas observadas del día anterior no equivalen a
   integrar previsiones meteorológicas futuras completas;
5. la evaluación con precipitación observada aísla el efecto de ET0, pero no
   valida el error real de la API de AEMET;
6. el horizonte de dos días ya aporta evidencia retrospectiva favorable, pero
   falta versionar el artefacto, verificarlo con entradas vivas y decidir cómo
   seleccionar automáticamente el horizonte según la fecha del último dato.

La decisión provisional pasa a ser **candidato favorable a integración
controlada**, no integración automática. El artefacto a un día ya está
serializado y dispone de respaldo; antes de sustituir la vía estable de media
reciente en la aplicación debe versionarse también el horizonte dos, resolver
la selección automática según la fecha del último dato y ejecutar una prueba
de regresión completa de Streamlit. Hasta entonces, la media reciente de siete
días continúa siendo la vía física ordinaria y la persistencia su referencia y
respaldo final.

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
octubre. Para recomendar el día 29 había que proyectar dos pasos y, en ese
momento, el experimento solo había validado uno. El sistema activó correctamente
persistencia en vez de extrapolar fuera de su alcance. La evaluación posterior
del horizonte dos no altera retroactivamente esa decisión segura.

La auditoría original registró el estado
`blocked_siar_publication_lag_for_same_day`. La barrera de evaluación se ha
reducido después al comprobar que Ridge a horizonte dos también mejora las
referencias en 2023–2025, pero la integración sigue bloqueada hasta versionar
ese artefacto y validar la selección automática de horizonte con entradas
vivas. AEMET no publica ET0 y no corrige por sí sola este desfase. El informe
de preparación se guarda en
`docs/data_samples/et0_operational_readiness.json` y la evidencia de la prueba
real en `docs/data_samples/et0_live_siar_smoke_2026-10-29.json`.

## Artefactos generados

- `src/analysis/audit_et0_availability.py`: inventario de fuentes disponibles;
- `src/data/prepare_et0_history.py`: normalización y control de calidad;
- `src/models/train_et0_multiyear.py`: entrenamiento y validación temporal;
- `src/analysis/evaluate_et0_multiyear.py`: bootstrap e impacto agronómico;
- `src/analysis/validate_et0_robustness.py`: ablación, baseline operativo y
  evaluación con origen rodante en 2023–2025;
- `src/models/export_et0_multiyear.py`: reajuste y versionado experimental;
- `src/dss/predict_et0.py`: inferencia con verificación y respaldo;
- `src/analysis/audit_et0_operational_readiness.py`: compatibilidad entre el
  contrato del modelo y las fuentes que alimentan actualmente Streamlit;
- `docs/data_samples/et0_multiyear_metrics.csv`: métricas de modelos;
- `docs/data_samples/et0_multiyear_predictions_2025.csv`: predicciones de prueba;
- `docs/data_samples/et0_multiyear_statistical_evidence.csv`: incertidumbre;
- `docs/data_samples/et0_multiyear_irrigation_impact.csv`: efecto en el riego;
- `docs/data_samples/et0_multiyear_evaluation_summary.json`: síntesis auditable.
- `docs/data_samples/et0_multiyear_robustness.csv` y
  `et0_multiyear_robustness_summary.json`: evidencia de robustez adicional;
- `docs/data_samples/et0_multiyear_*_Z06.*` y `*_BA08.*`: réplica geográfica;
- `docs/data_samples/et0_multiyear_geographic_validation.csv`: comparación
  consolidada de las tres estaciones.

Las pruebas automatizadas comprueban la construcción de objetivo a un día, la
ausencia de fuga temporal, la calidad del calendario, la reproducibilidad del
bootstrap y la aplicación única de Kc y precipitación.
