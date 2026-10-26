# Plan operativo de MLOps y control de deriva

## Objetivo

El plan evita que una aplicación aparentemente disponible siga generando
recomendaciones con datos atrasados, contratos rotos o modelos degradados. Se
aplica al sistema híbrido completo, no solo a los modelos predictivos.

## Indicadores y respuesta

| Capa | Indicador | Umbral inicial | Respuesta |
|---|---|---|---|
| Fuentes | Éxito de consulta SiAR y AEMET | 100 % en la ejecución; cualquier error queda registrado | Reintento limitado, aviso y uso de la última observación solo si sigue vigente |
| Vigencia | Antigüedad del último dato SiAR | Aviso si supera 2 días | Rebajar confianza o abstenerse según las reglas del DSS |
| Contrato | Columnas, tipos, unidades y claves | Cualquier cambio inesperado | Bloquear la transformación y conservar el raw para diagnóstico |
| Calidad | Ausentes, duplicados y rangos físicos | Desviación respecto al perfil de entrenamiento o regla incumplida | Marcar la incidencia y no imputar silenciosamente |
| Deriva de entrada | PSI o distancia de Wasserstein por variable y caso | Aviso orientativo a partir de PSI 0,20, revisable con experiencia | Abrir evaluación; no desplegar automáticamente |
| Rendimiento | MAE y sesgo por cultivo, estación y horizonte | Empeoramiento sostenido frente al modelo vigente y persistencia | Entrenar un candidato y evaluarlo en un bloque temporal posterior |
| AEMET | Error de ocurrencia y cantidad de lluvia por horizonte | Calibración y sesgo fuera del intervalo histórico | Revisar el posprocesado local sin sustituir la predicción oficial |
| Servicio | Latencia, errores y porcentaje de abstenciones | Tendencia adversa o incumplimiento del objetivo operativo | Diagnóstico y reversión a la última versión estable |

Los umbrales son de arranque y deben calibrarse cuando exista un historial
operativo suficiente. Un cambio estadístico no demuestra por sí solo una pérdida
agronómica.

## Ciclo de cambio controlado

1. Archivar entradas, hora de emisión, versión del código y recomendación.
2. Comparar distribuciones y rendimiento con el periodo de referencia.
3. Si existe una alerta persistente, entrenar un modelo candidato sin modificar
   el vigente.
4. Evaluar candidato, modelo vigente, persistencia y vía física en un bloque
   temporal no utilizado para selección.
5. Promover el candidato solo si mejora la métrica acordada, mantiene los
   controles de seguridad y documenta su alcance.
6. Conservar versión anterior, métricas y posibilidad de reversión.

En el estado actual, la falta de una referencia de campo limita la vigilancia a
la referencia SiAR y a la disponibilidad de las fuentes. Cuando se registren
riego aplicado, humedad y respuesta del cultivo, esas variables deberán formar
parte de la evaluación previa a cualquier despliegue.
