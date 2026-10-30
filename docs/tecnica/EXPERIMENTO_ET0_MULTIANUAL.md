# Experimento aislado de predicción multianual de ET0

## Alcance y separación de la entrega

Este documento conserva la trazabilidad técnica completa del experimento ya
integrado de forma controlada en `main`. Su objetivo es comprobar si una
predicción de ET0 entre uno y nueve días mejora las referencias físicas y bajo
qué condiciones puede participar en el DSS. No forma parte íntegra de la
memoria: el texto académico condensado se encuentra en el apartado 4.3.13 y en
[`SINTESIS_ET0_PARA_MEMORIA.md`](SINTESIS_ET0_PARA_MEMORIA.md). Aquí se mantienen
el protocolo, las evidencias reproducibles y la bitácora resumida para auditoría.

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

El objetivo se redefine para cada horizonte: ET0 en `t+h`, con `h=1…9`, en
mm/día. Se entrena y evalúa un artefacto independiente por horizonte. Las
variables se construyen solo con información disponible en `t` o antes:

- retardos de ET0 de 1, 2, 3, 7 y 14 días;
- medias móviles completas de ET0 de 3, 7 y 14 días; una ventana de 14 días
  exige literalmente 14 observaciones y no se calcula con una ventana parcial;
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

Los promedios por horizonte publicados en la memoria se recalculan desde el
CSV de robustez y se redondean a tres decimales. Por ello `h=1` aparece como
0,472 mm/día: su valor exacto vigente es 0,471970. No existe una discrepancia
entre la Tabla 4.18 y el conjunto de resultados versionado.

## Horizontes de uno a nueve días ante la latencia de SiAR

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

Los valores son MAE en mm/día. Se amplió a continuación el protocolo completo
a `h=1…9`, siempre construyendo las variables con información disponible en
`t` o antes. El MAE medio de las nueve ventanas estación-año fue:

| Horizonte | Ridge completo | Media 7 días | Persistencia estacional | Ventanas ganadas |
|---:|---:|---:|---:|---:|
| 1 | 0,472 | 0,551 | 0,663 | 9/9 |
| 2 | 0,524 | 0,587 | 0,781 | 9/9 |
| 3 | 0,546 | 0,607 | 0,831 | 9/9 |
| 4 | 0,557 | 0,622 | 0,865 | 9/9 |
| 5 | 0,565 | 0,636 | 0,868 | 9/9 |
| 6 | 0,567 | 0,650 | 0,891 | 9/9 |
| 7 | 0,571 | 0,666 | 0,900 | 9/9 |
| 8 | 0,571 | 0,687 | 0,898 | 9/9 |
| 9 | 0,570 | 0,708 | 0,899 | 9/9 |

Los valores son promedios descriptivos de MAE en mm/día, no nueve pruebas
externas independientes. Ridge ganó por valor puntual las 81 combinaciones.
El bootstrap por bloques mostró un intervalo completamente positivo frente a
la media de siete días en 63 de 81 ventanas: 9/9 en `h=1`, 6/9 en `h=2`, 6/9
en `h=3`, 5/9 en `h=4`, 5/9 en `h=5`, 7/9 en `h=6`, 8/9 en `h=7`, 8/9 en
`h=8` y 9/9 en `h=9`. Por tanto,
la señal media es favorable, pero la incertidumbre crece y no se afirma
superioridad estadística en cada estación-año individual.

La regla de exportación queda codificada: un horizonte solo se serializa si
Ridge completo presenta menor MAE puntual que la media móvil de siete días en
las nueve ventanas. Los nueve horizontes cumplieron esta regla; el manifiesto
conserva los 9/9 resultados que justifican cada artefacto.

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

La extensión `h=1…9` repite el mismo procedimiento, con 5.000 réplicas y
semilla 42, para cada combinación estación-año-horizonte y para tres contrastes:
Ridge completo frente a media móvil de siete días, frente a persistencia
corregida estacionalmente y frente a Ridge reducido. Las 243 comparaciones,
incluidas las de `h=2`, se conservan en
`docs/data_samples/et0_multiyear_robustness_uncertainty.csv`; las predicciones
diarias pareadas que permiten recomputarlas están en
`docs/data_samples/et0_multiyear_robustness_predictions.csv`.

La persistencia corregida se calcula como la última ET0 observada más el cambio
climatológico esperado entre origen y objetivo, estimado exclusivamente con
los años de entrenamiento. Ridge obtuvo un intervalo favorable frente a esta
referencia en 81 de 81 ventanas. Frente a la media móvil, 63 intervalos
excluyeron cero a favor de Ridge y 18 lo cruzaron; ninguno favoreció
significativamente a la media. El desglose de intervalos favorables / que
cruzan cero por horizonte fue 9/0, 6/3, 6/3, 5/4, 5/4, 7/2, 8/1, 8/1 y 9/0
para `h=1…9`.

En la ablación Ridge completo frente a Ridge reducido, solo 2 intervalos
favorecieron al completo, 74 cruzaron cero y 5 favorecieron al reducido. Por
horizonte, la clasificación completo / inconcluso / reducido fue 0/8/1,
1/8/0, 1/8/0, 0/9/0, 0/8/1, 0/8/1, 0/8/1, 0/8/1 y 0/9/0. Esta evidencia
impide atribuir una mejora estable a las variables meteorológicas auxiliares:
el valor principal procede de la historia de ET0 y la estacionalidad. El
resumen tabular regenerable se conserva en
`docs/data_samples/et0_multiyear_uncertainty_by_horizon.csv`.

## Relación entre latencia y siete días de recomendación

El horizonte del modelo se mide desde la última observación SiAR, mientras el
horizonte de la interfaz se mide desde el primer día solicitado. Con dos días
de latencia, recomendar hoy exige `h=2` y los siete días visibles utilizan
`h=2…8`; si el usuario empieza mañana, utilizan `h=3…9`. Por eso se entrenan
nueve horizontes aunque la interfaz muestre como máximo siete fechas. El motor
aplica una predicción ET0 distinta a cada día. Cuando un horizonte no cumple el
contrato, solo ese día vuelve a la media de siete días o queda no disponible;
no se presenta todo el periodo como si procediera del modelo.

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

## Cobertura operativa retrospectiva en 2026

Se descargó el intervalo 1 de enero–28 de octubre de 2026 por bloques de cuota
seguros y se simuló una recomendación de siete días para cada fecha de emisión,
con escenarios de uno y dos días de retraso fijo de publicación. La simulación
usa los datos finales disponibles y no reconstruye la hora real a la que SiAR
publicó cada jornada; mide disponibilidad del contrato, no latencia histórica
exacta.

| Estación | Retraso supuesto | Ridge | Media 7 días | Persistencia | No disponible |
|---|---:|---:|---:|---:|---:|
| AL01 | 1 día | 96,95 % | 3,00 % | 0,00 % | 0,05 % |
| AL01 | 2 días | 96,95 % | 2,57 % | 0,00 % | 0,48 % |
| BA08 | 1 día | 97,29 % | 2,66 % | 0,00 % | 0,05 % |
| BA08 | 2 días | 97,29 % | 2,28 % | 0,00 % | 0,44 % |
| Z06 | 1 día | 0,00 % | 1,36 % | 0,68 % | 97,97 % |
| Z06 | 2 días | 0,00 % | 0,87 % | 0,58 % | 98,55 % |

El CSV de campaña conserva 239 jornadas de Z06. La cifra de 13 corresponde
exclusivamente a la consulta del flujo operativo al endpoint público para el
intervalo solicitado, frente a 301 jornadas devueltas en AL01 y BA08. Tras
exigir 14 valores completos, esa consulta de Z06 no puede usar Ridge en la
simulación. El DSS no rellena los meses ausentes: utiliza un
respaldo solo durante siete días y después declara la recomendación como no
disponible. Esta es una limitación de cobertura de la fuente/estación, no un
fallo predictivo oculto. El detalle reproducible se conserva en
`docs/data_samples/et0_operational_coverage_2026.csv` y su resumen estructurado
en `et0_operational_coverage_2026_summary.json`.

La consulta pública se repitió el 30 de octubre de 2026 con 60 días solicitados
y volvió a devolver 13 registros, hasta el 28 de octubre. El selector permitió
Ridge a un día en la emisión anterior, imputando únicamente `lag_14d`; para el
objetivo del día 30 activó `mean_7d_fallback`, porque habrían sido necesarias
dos imputaciones y la política admite como máximo una. Por tanto, el 0 % de la
simulación con ventanas completas no debe presentarse como indisponibilidad
absoluta de Ridge: la cobertura efectiva depende del horizonte y del número de
entradas ausentes. La evidencia disponible no permite determinar si la
devolución parcial de Z06 responde a una incidencia, a un retraso de
publicación o a una limitación de la consulta. La evidencia viva queda archivada en
`docs/data_samples/et0_z06_60day_live_check.json`.

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
6. la comparación entre valores provisionales y posteriormente validados de
   SiAR requiere conservar instantáneas y esperar a que el proveedor consolide
   esas mismas fechas; no puede cerrarse retrospectivamente con una sola
   consulta;
7. que un intervalo bootstrap cruce cero no invalida el modelo, pero impide
   presentar esa ventana individual como una mejora estadísticamente concluyente;
8. la validación prospectiva está iniciada, pero necesita al menos 30 casos
   consolidados y pareados antes de mantener Ridge por evidencia viva.

La decisión es una **integración operativa controlada**, no una sustitución
incondicional del método físico. Los horizontes de uno a nueve días se
serializan porque cumplen la regla predefinida de 9/9 victorias puntuales frente
a la media móvil. La aplicación selecciona el horizonte según la fecha del
último dato. La media reciente de siete días, calculada con al menos tres
observaciones, continúa siendo el primer respaldo; la persistencia solo se usa
cuando tampoco existe esa ventana mínima. La puerta prospectiva puede devolver
automáticamente el sistema a la media de siete días.

## Preparación técnica para una integración controlada

Tras congelar la evaluación externa de 2025, Ridge se reajusta con todo el
histórico 2021–2025 de cada estación y horizonte. Los 27 artefactos —`h=1…9`
para AL01, Z06 y BA08— se conservan en
`models/experimental_et0_multiyear/` junto a un manifiesto que declara:

- estación, periodo y número de filas de entrenamiento;
- orden exacto de las variables de entrada;
- MAE de Ridge, persistencia y media móvil de siete días medidos antes del
  reajuste, sobre 2025;
- nombre y huella SHA-256 del artefacto;
- versiones de Python, NumPy, pandas, scikit-learn y joblib usadas al exportar;
- regla de selección y número de victorias frente a media 7 días por horizonte;
- estado explícito `operational_controlled_with_fallback`.

La inferencia de `src/dss/predict_et0.py` calcula la distancia entre el último
dato y la fecha objetivo y selecciona `h=1…9`. Exige al menos tres
retardos de ET0 válidos, verifica la huella del artefacto y no utiliza registros
de la fecha objetivo ni posteriores. También declara los valores concretos que
el `Pipeline` ha debido imputar y rechaza la inferencia si más de un valor de
entrada requiere imputación. Ante un horizonte superior, un modelo ausente
o manipulado, una estación no registrada, datos desactualizados o histórico
insuficiente, devuelve de forma trazable la media de ET0 de los últimos siete
días si contiene al menos tres observaciones. Solo después recurre a la última
ET0 observada; si tampoco existe, declara el resultado como no disponible.

Una comprobación de inferencia para el 1 de enero de 2026 produjo Ridge en AL01
y BA08, mientras Z06 activó correctamente el respaldo por falta de suficientes
retardos recientes. Este comportamiento confirma que el respaldo no es solo
una especificación documental. Después se construyó la tabla operativa diaria
con las mismas variables desde SiAR y se verificó en vivo en las tres
estaciones. AEMET no se usa para fabricar esas entradas: conserva el papel
separado de aportar la lluvia prevista que se descuenta tras `ET0 × Kc`.

## Auditoría de preparación operativa

### Estado final integrado

- se consulta una vez el histórico reciente de cada estación y se generan siete
  fechas con artefactos `h=1…9`, según la latencia real;
- las medias móviles requieren ventanas completas y como máximo se permite una
  entrada imputada por predicción;
- cada día conserva su método, horizonte, huella del modelo e intervalo
  empírico central del 80 %;
- la media de siete días es el respaldo prioritario, con al menos tres valores
  recientes y una antigüedad máxima de siete días;
- la persistencia solo actúa como último respaldo y nunca se usa información
  con más de siete días para emitir una dosis;
- AEMET mantiene un papel separado: únicamente aporta precipitación prevista
  para descontarla después de `ET0 × Kc`.

### Bitácora de incidencias ya resueltas

La bitácora no describe el estado vigente; documenta problemas encontrados y
su resolución para que no se confundan con limitaciones todavía abiertas.

| Incidencia detectada | Resolución aplicada | Evidencia principal |
|---|---|---|
| Los CSV de necesidades no incluían todas las variables de Ridge | Adaptador directo de observaciones diarias SiAR; no se imputan columnas completas | `et0_operational_readiness.json` |
| La latencia SiAR exigía más de un paso para recomendar hoy | Modelos independientes y versionados para `h=1…9` | `et0_live_siar_smoke_latest.json` |
| Z06 devolvía menos histórico que el solicitado | Máximo de una entrada imputada; después, media 7 días o no disponibilidad | `et0_z06_60day_live_check.json` |
| El selector terminaba en el último día del CSV | Extensión exclusiva de Kc hasta siete días, dentro del mismo mes y con `Kc > 0` | pruebas de la aplicación |
| Faltaba comprobar el flujo completo | Prueba viva en coliflor/AL01, alfalfa/Z06 y alcachofa/BA08 | `et0_streamlit_smoke_latest.json` |
| Los valores SiAR recientes podían revisarse | Conservación del primer valor, recuento de revisiones y consolidación tras siete días | `et0_prospective_validation_latest.json` |

Las instantáneas brutas de las pruebas vivas permanecen fuera de Git por ser
regenerables. Los informes públicos conservan valores redondeados, fechas,
métodos y causas de respaldo. La separación funcional es única en todo el
sistema: SiAR aporta observaciones y Kc; Ridge o la referencia física estiman
ET0; AEMET aporta únicamente la precipitación prevista que se descuenta una vez
después de `ETc = ET0 × Kc`.

## Validación prospectiva

Cada predicción Ridge emitida por Streamlit o por la prueba viva queda guardada
localmente en `data/raw/siar/prospective_et0/predictions.csv`, ruta excluida de
Git. La clave estación-fecha-huella hace la escritura idempotente y conserva la
fecha de emisión UTC, horizonte, ET0 predicha, media de siete días,
persistencia y versión exacta del artefacto. Cuando SiAR publica la ET0 de la
fecha objetivo, `src/analysis/update_et0_prospective_validation.py` reconsulta
el dato, cierra el registro y actualiza el MAE de Ridge y de ambas referencias.

El informe público `docs/data_samples/et0_prospective_validation_latest.json`
solo podrá pasar de `collecting` a `minimum_window_reached` al reunir 30 casos
validados; se recomiendan 60. Hasta entonces no se presentará el rendimiento
prospectivo como validación del modelo. La primera emisión se registró el 29 de
octubre de 2026 para AL01, Z06 y BA08 y permanece pendiente de observación consolidada.

La recogida deja de depender de que alguien abra Streamlit. El flujo programado
`.github/workflows/et0-prospective-daily.yml` consulta diariamente las tres
estaciones, emite `h=1…9` sin seleccionar días favorables y mantiene una rama
de evidencia revisable. La primera ET0 observada se marca como provisional; en
consultas posteriores se conserva el valor más reciente, se cuenta cualquier
revisión y solo se marca como consolidada tras siete días.

La puerta automática se evalúa al alcanzar 30 predicciones consolidadas y
pareadas. Después utiliza como máximo los 60 casos más recientes para evitar
que un histórico antiguo oculte una degradación actual. Ridge continúa
únicamente si reduce al menos un 5 % el MAE prospectivo de la media de siete
días; de lo contrario, la inferencia activa `physical_mean_7d`. Antes de 30
casos el estado es experimental y se muestra como evidencia en recogida. El
manifiesto fija un reentrenamiento anual tras cerrar y auditar la campaña; un
artefacto nuevo solo sustituirá al anterior si supera la referencia física en
validación temporal y conserva la puerta prospectiva. La interfaz muestra en
el bloque principal el intervalo empírico central del 80 % de ETc por día,
derivado de residuos de 2025 y etiquetado como incertidumbre histórica, no
como garantía.

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
- `src/analysis/run_et0_live_smoke.py`: prueba viva y archivo local de snapshots
  provisionales para su validación posterior;
- `src/analysis/compare_et0_provisional_snapshot.py`: comparación reproducible
  entre la instantánea y una reconsulta posterior;
- `src/dss/et0_prospective.py`: registro idempotente y cierre de predicciones;
- `src/analysis/update_et0_prospective_validation.py`: reconsulta de valores
  observados y actualización del informe prospectivo;
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
- `docs/data_samples/et0_live_siar_smoke_latest.json`: prueba operativa de los
  tres artefactos `h=2`.
- `docs/data_samples/et0_provisional_requery_latest.json`: primera comprobación
  del mecanismo de detección de revisiones.
- `docs/data_samples/et0_streamlit_smoke_latest.json`: prueba visual del flujo
  completo en los tres casos activos.
- `docs/data_samples/et0_multiyear_robustness_predictions.csv` y
  `et0_multiyear_robustness_uncertainty.csv`: pares diarios e intervalos por
  bloques para los nueve horizontes.
- `docs/data_samples/et0_multiyear_uncertainty_by_horizon.csv`: clasificación
  de los 243 intervalos por comparación y horizonte.

Las pruebas automatizadas comprueban los objetivos de uno a nueve días, el uso de
retardos de calendario reales, la ausencia de fuga temporal, la calidad del
calendario, la reproducibilidad del bootstrap, la integridad SHA-256 de los
artefactos, los respaldos y la aplicación única de Kc y precipitación. La
integración específica se incluye en la batería completa de 150 pruebas
superadas, junto con la compilación correcta de `src` y una consulta real
satisfactoria en las tres estaciones. La permanencia de Ridge se somete además
a la puerta prospectiva; la integración en `main` no elimina el respaldo ni
convierte la prueba viva en validación agronómica.
