# Síntesis del experimento predictivo multianual de ET0

## Objetivo y encaje en el DSS

El experimento evalúa si la evapotranspiración de referencia (ET0) puede
predecirse con mayor precisión que mediante referencias físicas simples y si
esa predicción puede alimentar el DSS durante siete días. La ET0 pertenece a la
estación meteorológica, no al cultivo. El sistema transforma posteriormente
cada predicción mediante `ETc = ET0 × Kc` y descuenta una sola vez la lluvia
prevista aprovechable de AEMET.

La interfaz muestra siete fechas, pero el horizonte del modelo se cuenta desde
la última observación SiAR. Con dos días de latencia, hoy requiere `h=2` y el
séptimo día `h=8`; si se empieza mañana se requieren `h=3…9`. Por ello se
entrenaron 27 artefactos: nueve horizontes para AL01, Z06 y BA08.

## Datos y prevención de fuga temporal

Se utilizaron observaciones diarias oficiales SiAR de 2021–2025. Las variables
incluyen retardos de ET0 de 1, 2, 3, 7 y 14 días; medias completas de 3, 7 y 14
días; meteorología observada en `t`; y codificación cíclica de la fecha objetivo.
Una media de 14 días exige 14 observaciones: no se denomina así a una ventana
parcial. Para cada `h`, el objetivo es ET0 en `t+h` y todas las entradas
pertenecen a `t` o antes.

La evaluación emplea origen rodante: 2021–2022 para probar 2023, 2021–2023 para
2024 y 2021–2024 para 2025. Se comparan Ridge completo, Ridge reducido a ET0 y
estacionalidad, persistencia, persistencia corregida estacionalmente y media
móvil de siete días. El bootstrap pareado utiliza bloques circulares de siete
días, 5.000 réplicas y semilla 42.

## Resultados

Ridge completo obtuvo menor MAE puntual que la media de siete días en las 81
combinaciones estación-año-horizonte. Los MAE medios de las nueve ventanas
fueron:

| h | Ridge | Media 7 días | Persistencia estacional |
|---:|---:|---:|---:|
| 1 | 0,472 | 0,551 | 0,663 |
| 2 | 0,524 | 0,587 | 0,781 |
| 3 | 0,546 | 0,607 | 0,831 |
| 4 | 0,557 | 0,622 | 0,865 |
| 5 | 0,565 | 0,636 | 0,868 |
| 6 | 0,567 | 0,650 | 0,891 |
| 7 | 0,571 | 0,666 | 0,900 |
| 8 | 0,571 | 0,687 | 0,898 |
| 9 | 0,570 | 0,708 | 0,899 |

El baseline de persistencia corregida no es una etiqueta: parte de la última
ET0 observada y suma el cambio climatológico esperado entre el día de origen y
el día objetivo, calculado solo con los años de entrenamiento. Ridge completo
obtuvo intervalos positivos frente a esta referencia en las 81 ventanas.

La clasificación de los demás intervalos por horizonte es:

| h | Ridge frente a media 7 d: favorable / cruza cero | Completo frente a reducido: favorable / cruza cero / favorable al reducido |
|---:|---:|---:|
| 1 | 9 / 0 | 0 / 8 / 1 |
| 2 | 6 / 3 | 1 / 8 / 0 |
| 3 | 6 / 3 | 1 / 8 / 0 |
| 4 | 5 / 4 | 0 / 9 / 0 |
| 5 | 5 / 4 | 0 / 8 / 1 |
| 6 | 7 / 2 | 0 / 8 / 1 |
| 7 | 8 / 1 | 0 / 8 / 1 |
| 8 | 8 / 1 | 0 / 8 / 1 |
| 9 | 9 / 0 | 0 / 9 / 0 |

En total, frente a media 7 días, 63 de 81 intervalos excluyeron cero a favor
de Ridge y 18 lo cruzaron; ninguno favoreció significativamente a la media. En
la ablación completo frente a reducido, 2 intervalos favorecieron al completo,
74 cruzaron cero y 5 favorecieron al reducido. Por tanto, existe evidencia
consistente de mejora respecto a los dos respaldos físicos, pero no de que la
meteorología auxiliar aporte una ganancia estable sobre ET0 histórica y
estacionalidad. El detalle regenerable está en
`docs/data_samples/et0_multiyear_uncertainty_by_horizon.csv`.

La regla de exportación no es manual: solo se serializa un horizonte si Ridge
supera puntualmente a media 7 días en las nueve ventanas. Los nueve horizontes
cumplieron 9/9. El manifiesto conserva periodo, variables, métricas externas,
versiones, huella SHA-256 e intervalo residual central del 80 %.

## Funcionamiento operativo y seguridad

Streamlit consulta SiAR una sola vez y construye una predicción independiente
para cada una de las siete fechas. Cada día utiliza su artefacto `h`
correspondiente, su Kc y la precipitación AEMET disponible. La tabla identifica
si se usó Ridge o respaldo y muestra un rango empírico de ETc. Ese intervalo
procede de residuos de 2025 y no representa una garantía meteorológica.

El contrato operativo exige al menos tres retardos ET0 válidos, medias móviles
completas, huella correcta y como máximo una entrada imputada. Si falla, se usa
la media de siete días con al menos tres observaciones recientes. La
persistencia es el último respaldo. Ninguno se aplica si la última ET0 tiene
más de siete días; en tal caso se declara «no disponible».

## Cobertura 2026

Con siete fechas por emisión y retrasos supuestos de uno/dos días, Ridge cubrió
el 96,95 % de AL01 y el 97,29 % de BA08. En Z06 la API solo devolvió 13 jornadas
entre enero y octubre: Ridge tuvo 0 % de cobertura y más del 97,9 % de las
fechas quedaron no disponibles. El resultado se muestra explícitamente porque
la calidad predictiva condicionada a datos no equivale a disponibilidad del
servicio.

## Validación prospectiva y mantenimiento

Una acción diaria emite `h=1…9` para las tres estaciones sin depender de que un
usuario abra la aplicación. Guarda la primera ET0 publicada como provisional,
revisa cambios posteriores y consolida el valor tras siete días. Con menos de
30 predicciones consolidadas, el estado permanece experimental. A partir de 30,
Ridge continúa solo si su MAE es menor que el de media 7 días; en caso contrario
la aplicación activa automáticamente el respaldo físico. Se recomiendan 60
casos antes de adoptar una conclusión estable.

El reentrenamiento se plantea anualmente, después de cerrar y auditar la
campaña. Un artefacto nuevo no sustituye al anterior si no supera de nuevo la
referencia física en validación temporal.

## Conclusión y limitaciones

El experimento justifica una integración controlada de Ridge para siete días en
estaciones con cobertura suficiente. No demuestra rendimiento nacional, ahorro
de agua ni precisión de AEMET en parcela. La escasa disponibilidad de Z06, los
18 intervalos no concluyentes frente a media 7 días y la débil aportación de
variables auxiliares limitan la generalización. La arquitectura responde a esas
limitaciones con trazabilidad diaria, respaldo físico, incertidumbre visible,
monitorización prospectiva y posibilidad de desactivación automática.
