# Estado actual y trabajo pendiente del TFM

Fecha de revisión: 24 de octubre de 2026

## 1. Diagnóstico general

La memoria tiene contenido en los capítulos 1 a 6. El piloto inicial de
pimiento en `AL01` (La Mojonera, Almería) durante 2025 permanece como referencia
de la ETL y del motor. La aplicación Streamlit admite ahora los nueve CSV SiAR
descargados para tres estaciones, seis cultivos y campañas de 2025 o 2026. El
experimento predictivo nuevo agrupa esos archivos en seis casos independientes:
1776 filas de origen y 1584 jornadas completas y activas. La comparación
temporal y el reajuste se documentan en `docs/memoria/04_03_desarrollo_evaluacion_modelo_predictivo.md`
y en `docs/data_samples/model_retraining_2026.json`. No existe un modelo
único que se haya generalizado a todos los cultivos.

El piloto estima la necesidad neta calculada por SiAR y propone dosis diarias
y semanales. No se ha medido el riego aplicado, el ahorro de agua ni la respuesta
del cultivo. Tampoco se ha demostrado que el resultado se generalice a otras
estaciones, campañas o cultivos. La selección en la interfaz se limita a los
casos ya descargados; la extracción arbitraria y la operación continua siguen
siendo objetivos del producto, no funciones validadas del prototipo.

La integración de ETc reentrenada y AEMET se describe en
`docs/INTEGRACION_ETC_AEMET_2026.md`. La app carga los seis modelos versionados,
pero el cálculo físico conserva la dosis en cinco casos por menor MAE de prueba;
solo algodón favorece al modelo y está fuera de ciclo en esta revisión.

## 2. Estado por capítulo

| Apartado | Estado | Revisión pendiente |
|---|---|---|
| 1. Introducción y objetivos | Redactado | Distinguir con claridad la visión de producto (elegir zona y cultivo) del piloto fijo realmente implementado. |
| 2. Marco teórico y estado del arte | Redactado | Cotejar citas, referencias, DOI y formato final. |
| 3. Metodología y arquitectura | Redactado | Verificar que las tecnologías previstas no se presentan como desplegadas. |
| 4. Procesamiento y Machine Learning | Piloto original y reentrenamiento independiente en seis casos documentados | Revisar reproducción de cifras y que los resultados no se describan como validación agronómica ni como mejora demostrada. |
| 5. DSS y resultados | Motor físico y modelos ETc conectados a la app con control comparativo | Validar prospectivamente con usuarios y datos de campo; falta histórico de previsiones alineado. |
| 6. Conclusiones | Redactado | Revisar con el equipo el grado de cumplimiento de objetivos y las afirmaciones de alcance. |
| Elementos preliminares y anexos | Revisión de contenido y maquetación completada | La versión candidata está en `docs/memoria/TFM_revision_final_contenido_2026-10-24.docx` y `docs/memoria/TFM_revision_final_2026-10-24.pdf`. Se revisaron las 85 páginas y los índices con la paginación exportada. El abstract en inglés se eliminó por decisión del equipo. Queda la lectura final del equipo y la confirmación agronómica del encuadre del pimiento. |

## 3. Qué demuestra el repositorio

- Integración y normalización de datos climáticos SiAR y predicciones AEMET.
- Incorporación del CSV oficial de necesidades hídricas del cultivo con sus
  metadatos, descargado manualmente de la web de SiAR.
- Capas `raw`, `interim` y `processed`, controles de calidad y trazabilidad.
- Comparación temporal de Persistencia, Ridge, Random Forest, KNN, SVR y
  XGBoost para la referencia de SiAR. El nuevo experimento evalúa seis casos
  por separado: persistencia se selecciona en cinco; Ridge se selecciona en
  coliflor, pero no supera a persistencia en la prueba final.
- Motor de recomendación con reglas, dosis neta y bruta, conversión opcional a
  volumen, advertencias y explicación; aplicación Streamlit y línea de comandos.
- Validación técnica frente a SiAR, análisis por horizonte, 13 escenarios y
  97 pruebas automáticas. La referencia es calculada, no riego real observado.

Los comandos para reproducir cada fase figuran en el README. No existe un único
comando que regenere íntegramente todas las salidas de los capítulos 4 y 5.
Las extracciones nuevas necesitan credenciales y respetar las cuotas de cada
API; el motor puede ejecutarse con el CSV oficial ya versionado sin volver a
consultar las APIs.

## 4. Límites técnicos que no deben ocultarse

| Componente | Estado real del piloto | Tratamiento en la memoria |
|---|---|---|
| Elección de estación y cultivo | La aplicación permite elegir entre los nueve CSV verificados; no ofrece cualquier combinación nacional. El experimento predictivo agrupa campañas del mismo cultivo y estación. | Describir la selección limitada implementada y la libre selección como evolución. |
| ET0 y lluvia previstas | No existe un histórico de emisiones alineado con la campaña de 2025; la previsión de ET0 puede suministrarse manualmente al motor. | No atribuir al piloto una validación predictiva con pronósticos históricos. |
| Momento de riego | El motor estima cuánto regar y avisa ante lluvia; no calcula un balance hídrico del suelo. | No afirmar que decide el día óptimo de riego. |
| Disponibilidad de agua | La dotación la introduce el usuario; MITECO no se integra como asignación parcelaria. | Declarar la limitación hidrológica. |
| MySQL, Apache Hop, Docker y PySpark | No implementados en el piloto. | Mantenerlos como arquitectura objetivo o línea futura. |
| Power BI o Tableau | Sustituidos por una aplicación Streamlit funcional. | Describir la sustitución y su motivo. |

## 5. Revisión de cierre antes de la entrega

1. Confirmar con el tutor que la portada, el resumen español, los índices y el
   anexo A de la versión de revisión cumplen las normas del máster; no se
   incluye abstract en inglés por decisión del equipo.
2. La guía `docs/DEMO_TFM.md` ya incluye el recorrido público comprobado el
   25/10/2026, la lectura del CSV y la alternativa retrospectiva local. La
   instalación desde un clon limpio queda como comprobación técnica opcional:
   el recorrido de evaluación previsto usa GitHub y la app pública.
3. Revisar todas las referencias cruzadas, pies de tablas y figuras, citas,
   bibliografía, unidades, redondeos y ortografía. Confirmar el origen y la
   aplicabilidad al pimiento al aire libre del calendario y los coeficientes
   `Kc` utilizados por SiAR.
4. Asegurar que el Word y el PDF finales representan la misma versión; revisar
   visualmente todas las páginas y evitar tablas partidas de forma incómoda.
5. Revisar las evidencias que verá el tutor en GitHub, comprobar que no se
   versionan tokens, credenciales ni datos sensibles y contrastar la memoria
   con la app pública. El 25/10 pasaron 33 pruebas focalizadas del motor,
   AEMET, ETc y la demo local; la suite completa y `AppTest` quedan como
   comprobaciones técnicas adicionales. La app pública se comprobó manualmente
   con coliflor, alfalfa y alcachofa activos, pimiento fuera de ciclo y un
   escenario de lluvia hipotética. Una emisión AEMET antigua se recibió pero
   no se aplicó a la dosis, como corresponde.
6. El anexo de la memoria ya incluye el
   [enlace público de Streamlit](https://tfm-regadio-dss-adrianpl15.streamlit.app/).
   El 25/10/2026 se comprobó el CSV descargado: siete días, dosis y volumen
   coherentes con los indicadores redondeados de la pantalla. El recorrido está
   en `docs/DEMO_TFM.md`; verificarlo de nuevo el día de la presentación.
7. La versión pública y la memoria candidata están en el fork
   `AdrianPL15/tfm-regadio-dss`, cuya rama `main` contiene también las
   correcciones de la demo y el recorrido del README. Conservar el fork para la
   entrega mantiene visibles las pull requests; revisar cambios nuevos del
   repositorio original antes de decidir si incorporarlos.

Las prioridades posteriores a la entrega son ampliar campañas y estaciones,
archivar previsiones por fecha de emisión, incorporar datos de suelo y riego
aplicado, validar con usuarios y ensayar en campo antes de afirmar ahorro o
utilidad agronómica generalizable.

## 6. Criterio de cierre

El TFM estará listo para entregar cuando una persona pueda seguir las
instrucciones del repositorio, reproducir el caso piloto y sus pruebas, y
comprobar que la memoria describe exactamente esos resultados y sus límites.
El archivo `docs/PENDIENTES.docx` es una nota histórica y no representa el
estado actual del proyecto.
