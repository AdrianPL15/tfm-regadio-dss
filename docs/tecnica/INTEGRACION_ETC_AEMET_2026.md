# Integración de modelos SiAR de ETc y previsión AEMET

## Qué calcula la app

Para recomendar hoy o mañana, la app consulta el calendario y los datos recientes de
SiAR. Un modelo entrenado por cultivo y estación estima la **ETc antes de
lluvia**. A continuación, si AEMET aporta una cantidad de precipitación
horaria utilizable, el motor descuenta la fracción aprovechable indicada por el
usuario y divide la necesidad resultante por la eficiencia del sistema de
riego. Una probabilidad de lluvia sin cantidad en mm no equivale a lluvia cero.
Para hoy se suman únicamente las horas futuras respecto a la consulta; para
mañana se exige la cobertura horaria completa. Si no hay una emisión reciente
o una cantidad utilizable, se muestra la dosis base sin descuento de lluvia.

El modelo de ETc y la previsión AEMET cumplen funciones diferentes: AEMET no
fue una variable del entrenamiento y la lluvia no se descuenta dos veces. El
primer día puede usar el modelo; los días 2 a 7 conservan el cálculo físico
orientativo, porque el experimento solo evaluó predicciones rodantes a un día.
Los modelos anteriores de necesidad neta siguen documentados en 4.3 como
experimento, pero no son los artefactos que consulta Streamlit.

## Selección operativa

Se entrenaron seis casos con los nueve CSV SiAR disponibles. La selección del
algoritmo por caso usa tres cortes temporales del periodo de desarrollo. El
15 % final quedó reservado para prueba. En esa misma prueba se comparó el
modelo elegido con el cálculo físico ya presente en la app: media de ET0 de
las últimas siete jornadas × Kc. El modelo solo sustituye el cálculo físico
cuando su MAE de prueba es menor. En otros casos se ejecuta y se muestra como
comparación, mientras la dosis principal mantiene el método físico. Usar el
tramo de prueba para esta decisión operativa implica que esos MAE **no son una
evaluación independiente del sistema completo ya seleccionado**.

| Cultivo y estación | Modelo seleccionado | MAE modelo (mm/día) | MAE físico (mm/día) | Método para la dosis |
|---|---|---:|---:|---|
| Pimiento AL01 | Persistencia | 0,390 | 0,295 | Físico |
| Coliflor AL01 | Ridge | 0,762 | 0,636 | Físico |
| Maíz Z06 | Persistencia | 0,718 | 0,556 | Físico |
| Algodón BA08 | Persistencia | 0,410 | 0,434 | Modelo |
| Alfalfa Z06 | Persistencia | 0,556 | 0,531 | Físico |
| Alcachofa BA08 | Persistencia | 0,482 | 0,455 | Físico |

El algodón está fuera de ciclo en la fecha de esta revisión (24/10/2026), de
modo que los tres cultivos activos ahora muestran la predicción del modelo
como contraste y mantienen la dosis física. La diferencia de algodón es
pequeña y tampoco acredita una mejora agronómica. No se dispone de riego real
observado, sensores de suelo ni un archivo de previsiones AEMET emitidas antes
de cada fecha histórica. La lluvia aprovechable es una hipótesis editable.

## Reproducción y archivos

```powershell
python -m src.models.train_etc_for_dss
python -m unittest tests.test_deployed_etc_dss
streamlit run src/dss/app_streamlit.py
```

El entrenamiento genera el informe
[`etc_model_deployment_2026.json`](../data_samples/etc_model_deployment_2026.json)
y seis modelos pequeños en `models/deployed_etc_2026/`. Se versionan estos
artefactos concretos para que Streamlit Community Cloud pueda cargarlos sin
entrenar al iniciar. La app usa `src/dss/predict_etc.py` para comprobar cultivo,
estación, fecha, Kc y datos anteriores a la consulta. Si el modelo falta, está
anticuado o no hay ETc observada reciente, usa el cálculo físico y muestra un
aviso. La API de AEMET sigue siendo opcional para una dosis base, pero es
necesaria para descontar la lluvia prevista real.

Si SiAR aún no ha publicado uno o dos días intermedios, el modelo puede
avanzar recursivamente hasta el día solicitado para mostrar una comparación provisional.
Esa extrapolación de dos o tres pasos no fue evaluada y nunca se usa para
determinar la dosis principal; se muestra un aviso. Solo una predicción directa
de un día puede superar el control de despliegue.

Los nombres históricos de las columnas de retardos y acumulados contienen
`net_irrigation_need`; en **este** experimento sus valores son retardos de
ETc. Es una reutilización del esquema de entrenamiento y queda declarada para
evitar interpretarlos como necesidad neta. Antes de ampliar el modelo conviene
renombrar el esquema y añadir predictores meteorológicos archivados con su
fecha de emisión.
