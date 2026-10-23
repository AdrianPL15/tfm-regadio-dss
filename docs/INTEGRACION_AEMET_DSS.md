# Integración inicial de AEMET en el DSS

## Qué se ha conectado

El proyecto ya podía consultar AEMET OpenData y transformar sus JSON. Ahora `src/dss/aemet_forecast.py` convierte la predicción municipal **actual** en una tabla diaria utilizable por el motor. Relacionamos AL01 con Almería (`04013`), Z06 con Ejea de los Caballeros (`50095`) y BA08 con Don Benito (`06044`). Son municipios de referencia, no la posición exacta de las parcelas ni equivalentes a las estaciones SiAR. Los códigos se comprobaron en las [páginas municipales oficiales de AEMET](https://www.aemet.es/es/eltiempo/prediccion/municipios/ejea-de-los-caballeros-id50095) y en el [inventario de AEMET OpenData](https://opendata.aemet.es/dist/).

El producto diario aporta la probabilidad de precipitación. El horario aporta cantidades previstas en mm durante unas 48 horas; se suman solo las horas futuras con valor numérico y se informa de cuántas horas cubren. Fuera de esa cobertura la cantidad queda **ausente**, aunque exista probabilidad. No se transforma una probabilidad en mm ni se calcula ET0 a partir de UV o temperatura. El fichero normalizado conserva municipio, emisión diaria y horaria, fecha válida, probabilidad, cantidad y estado de cobertura.

El 23/10/2026 se hizo una consulta real para Almería con la clave local. Devolvió siete días; los tres primeros tenían cantidad horaria disponible y los restantes solo probabilidad. Se guardó una instantánea en `data/raw/aemet/forecast/municipality=04013` y su tabla en `data/interim/aemet/forecast/municipality=04013`. Ambas carpetas están excluidas de Git: se preserva el JSON original para futuras comparaciones sin publicar claves ni confundirlo con datos de 2025.

## Cómo influye la lluvia en la dosis

La recomendación base sigue siendo la del capítulo 5: `ET0 prevista × Kc` cuando se aporta ET0 prevista, o media de ET0 SiAR de siete días anteriores × Kc. Su dosis bruta es necesidad neta dividida por eficiencia. AEMET no proporciona en esos productos una ET0 directa. La lluvia prevista activa avisos, pero **por defecto no se descuenta**: precipitación prevista y precipitación efectiva en la zona radicular no son iguales.

La aplicación incorpora un **escenario condicionado** que permite probar cuánto cambiaría la dosis si se cumpliera una lluvia indicada y si una fracción editable de ella fuese aprovechable:

`necesidad condicionada = max(0, necesidad base − lluvia prevista × fracción efectiva hipotética)`

La fracción es una **hipótesis introducida por el usuario**, no un parámetro calibrado; el valor mostrado no está validado como riego óptimo. Se presentan la necesidad antes de lluvia, los mm descontados, la dosis condicionada y un aviso de recalcular tras la lluvia real. El modo histórico de la demo utiliza una lluvia **manual simulada**, expresamente etiquetada; nunca se le aplica una previsión emitida en octubre de 2026. La prueba automatizada utiliza 12 mm hipotéticos y una fracción del 25 % para verificar un descuento de 3 mm, sin alterar el CSV de SiAR. Esta prueba valida la aritmética y la trazabilidad, no la idoneidad agronómica del 25 %.

La precipitación aprovechable depende de suelo, intensidad, escorrentía, almacenamiento y estado hídrico. La [FAO explica](https://www.fao.org/4/s2022e/s2022e03.htm) por qué no puede suponerse que toda lluvia caída satisface las necesidades del cultivo. Antes de convertir este escenario en dosis operativa automática habría que medir o estimar esas condiciones y evaluar el riesgo de infrarriego.

## Uso y reproducción

Con `AEMET_API_KEY` guardada únicamente en `.env`, se puede archivar una predicción actual desde la raíz del repositorio:

```powershell
python -m src.data.archive_aemet_forecast --municipio 04013
```

El comando conserva los dos JSON recibidos y un CSV diario normalizado bajo `data/raw` y `data/interim`. No sobrescribe una emisión anterior con contenido diferente. Conviene programar esta captura periódica para reunir el **histórico de previsiones emitidas** que falta para evaluar modelos con AEMET. La climatología observada de 2025 no sustituye a las previsiones que hubieran estado disponibles entonces.

La app permite consultar la predicción AEMET actual si hay clave local o un secreto `AEMET_API_KEY` en Streamlit. La muestra separada de las recomendaciones históricas. La interfaz no publica la clave. Si no está configurada, la consulta falla con un mensaje controlado y el resto de la demo sigue funcionando. El motor también acepta un CSV de previsión con `date`, `precipitation_mm` y/o `precipitation_probability_pct` y, opcionalmente, `issued_at` y `et0_mm`. Para explorar el escenario desde la línea de comandos:

```powershell
python -m src.dss.recommend --fecha 2025-06-28 --prevision ruta/al/escenario.csv --fraccion-lluvia 0.25
```

El usuario debe identificar ese CSV como escenario o como previsión realmente archivada. El motor rechaza una fecha de emisión posterior a la consulta. El 23/10/2026 se añadieron cuatro CSV SiAR iniciales y posteriormente alfalfa Z06 y alcachofa BA08 ([inventario y límites](CAMPANAS_SIAR_2026.md)). Coliflor AL01, alfalfa Z06 y alcachofa BA08 tienen Kc positivo y dato reciente para el 24/10; pimiento, maíz y algodón se muestran como históricos, sin aplicarles AEMET actual. La aplicación puede calcular una **estimación condicionada** para mañana usando un Kc prolongado dentro del mes y la predicción AEMET emitida hoy. No se ha modificado ningún dato observado SiAR para ocultar la ausencia de datos futuros. El comando `--aemet-live` conserva su contrato anterior y no realiza esa proyección de Kc; la funcionalidad de mañana está en la interfaz Streamlit.

## Qué falta para incorporar AEMET a los modelos

Los modelos de `src/models/train_evaluate.py` y la nueva evaluación de maíz y algodón aún utilizan solo SiAR y variables históricas. Para entrenarlos con AEMET se necesita una tabla con `municipio`, `issued_at`, `valid_date`, horizonte y predicción tal como existía **antes** del día objetivo, alineada con la estación/cultivo SiAR correspondiente. Hay que reunir varias campañas y separar entrenamiento y prueba en el tiempo. Después se comparará el modelo con y sin predicción AEMET frente a la misma referencia SiAR, midiendo MAE, sesgo, error por horizonte y episodios de lluvia. Sin las previsiones originales de 2025 no es legítimo presentar la meteorología observada de ese año como si hubiera sido un pronóstico.

`src/features/build_aemet_model_table.py` ya construye esa unión de forma conservadora: selecciona por fecha y municipio la última previsión emitida **antes de las 00:00 del día objetivo** y conserva su horizonte. Para probarlo:

```powershell
python -m src.features.build_aemet_model_table
```

La instantánea AEMET del 23/10/2026 no puede incorporarse a la evaluación de las campañas de 2025. Tampoco basta una sola emisión actual para medir de manera fiable la mejora en las campañas de 2026: se requiere archivar muchos pronósticos a lo largo del ciclo y evaluar las predicciones como se conocían entonces. No se ha entrenado ni atribuido una mejora a un modelo AEMET con muestras temporalmente incompatibles.
