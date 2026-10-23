# Estado actual y trabajo pendiente del TFM

Fecha de revisión: 23 de octubre de 2026

## 1. Diagnóstico general

La memoria tiene contenido en los capítulos 1 a 6. El repositorio implementa
una prueba de concepto para pimiento al aire libre en la estación SiAR `AL01`
(La Mojonera, Almería) durante la campaña de mayo a septiembre de 2025. La ETL,
la comparación de seis enfoques predictivos, el motor de recomendaciones y la
aplicación Streamlit cuentan con código y evidencias. El conjunto oficial de
necesidades tiene 150 fechas, de las que 148 son válidas para el análisis;
existe un catálogo de 88 variables. La validación técnica documenta 13
escenarios. Las 61 pruebas automáticas se ejecutaron correctamente en el
entorno local del proyecto el 23/10/2026.

El piloto estima la necesidad neta calculada por SiAR y propone dosis diarias
y semanales. No se ha medido el riego aplicado, el ahorro de agua ni la respuesta
del cultivo. Tampoco se ha demostrado que el resultado se generalice a otras
estaciones, campañas o cultivos. La selección dinámica de caso y la operación
continua siguen siendo objetivos del producto, no funciones validadas del
prototipo.

## 2. Estado por capítulo

| Apartado | Estado | Revisión pendiente |
|---|---|---|
| 1. Introducción y objetivos | Redactado | Distinguir con claridad la visión de producto (elegir zona y cultivo) del piloto fijo realmente implementado. |
| 2. Marco teórico y estado del arte | Redactado | Cotejar citas, referencias, DOI y formato final. |
| 3. Metodología y arquitectura | Redactado | Verificar que las tecnologías previstas no se presentan como desplegadas. |
| 4. Procesamiento y Machine Learning | Implementado y documentado para el piloto | Revisar reproducción de cifras y que los resultados no se describan como validación agronómica. |
| 5. DSS y resultados | Implementado y documentado para el piloto | Validar con usuarios y datos de campo en una fase posterior; falta histórico de previsiones alineado. |
| 6. Conclusiones | Redactado | Revisar con el equipo el grado de cumplimiento de objetivos y las afirmaciones de alcance. |
| Elementos preliminares y anexos | Versión de revisión preparada | Portada, resumen en español, palabras clave, índices y anexo A están en `docs/memoria/TFM_revision_coherencia_2026-10.docx` y su PDF de 85 páginas. El abstract en inglés se eliminó por decisión del equipo; comprobar los requisitos formales antes de entregar. |

## 3. Qué demuestra el repositorio

- Integración y normalización de datos climáticos SiAR y predicciones AEMET.
- Incorporación del CSV oficial de necesidades hídricas del cultivo con sus
  metadatos, descargado manualmente de la web de SiAR.
- Capas `raw`, `interim` y `processed`, controles de calidad y trazabilidad.
- Comparación temporal de Persistencia, Ridge, Random Forest, KNN, SVR y
  XGBoost para la referencia de SiAR. La persistencia es la mejor línea base
  del piloto; los cinco algoritmos de aprendizaje no la mejoran de forma
  estable.
- Motor de recomendación con reglas, dosis neta y bruta, conversión opcional a
  volumen, advertencias y explicación; aplicación Streamlit y línea de comandos.
- Validación técnica frente a SiAR, análisis por horizonte, 13 escenarios y
  61 pruebas automáticas. La referencia es calculada, no riego real observado.

Los comandos para reproducir cada fase figuran en el README. No existe un único
comando que regenere íntegramente todas las salidas de los capítulos 4 y 5.
Las extracciones nuevas necesitan credenciales y respetar las cuotas de cada
API; el motor puede ejecutarse con el CSV oficial ya versionado sin volver a
consultar las APIs.

## 4. Límites técnicos que no deben ocultarse

| Componente | Estado real del piloto | Tratamiento en la memoria |
|---|---|---|
| Elección de estación y cultivo | La extracción climática admite estación y periodo; la ETL de necesidades toma el CSV más recientemente modificado. La aplicación utiliza un caso fijo. | Presentar la selección dinámica como evolución, no como función actual. |
| ET0 y lluvia previstas | No existe un histórico de emisiones alineado con la campaña de 2025; la previsión de ET0 puede suministrarse manualmente al motor. | No atribuir al piloto una validación predictiva con pronósticos históricos. |
| Momento de riego | El motor estima cuánto regar y avisa ante lluvia; no calcula un balance hídrico del suelo. | No afirmar que decide el día óptimo de riego. |
| Disponibilidad de agua | La dotación la introduce el usuario; MITECO no se integra como asignación parcelaria. | Declarar la limitación hidrológica. |
| MySQL, Apache Hop, Docker y PySpark | No implementados en el piloto. | Mantenerlos como arquitectura objetivo o línea futura. |
| Power BI o Tableau | Sustituidos por una aplicación Streamlit funcional. | Describir la sustitución y su motivo. |

## 5. Trabajo imprescindible antes de la entrega

1. Confirmar con el tutor que la portada, el resumen español, los índices y el
   anexo A de la versión de revisión cumplen las normas del máster; no se
   incluye abstract en inglés por decisión del equipo.
2. Revisar la guía `docs/DEMO_TFM.md` y probar la demostración local desde un
   clon limpio antes de la entrega final.
3. Revisar todas las referencias cruzadas, pies de tablas y figuras, citas,
   bibliografía, unidades, redondeos y ortografía. Confirmar el origen y la
   aplicabilidad al pimiento al aire libre del calendario y los coeficientes
   `Kc` utilizados por SiAR.
4. Asegurar que el Word y el PDF finales representan la misma versión; revisar
   visualmente todas las páginas y evitar tablas partidas de forma incómoda.
5. Ejecutar el flujo documentado y las pruebas en un entorno reproducible,
   registrar versiones de dependencias y comprobar que no se versionan tokens,
   credenciales ni datos sensibles.
6. Incorporar al anexo de la memoria final el
   [enlace público de Streamlit](https://tfm-regadio-dss-adrianpl15.streamlit.app/),
   ya comprobado sin iniciar sesión el 23/10/2026. Abrir y revisar también el
   CSV descargado desde la app; la guía está en `docs/STREAMLIT_DESPLIEGUE.md`.
7. La rama de revisión ya se integró en `main` mediante la PR #8 y se creó el
   fork `AdrianPL15/tfm-regadio-dss` para el despliegue. Mantener identificados
   ambos repositorios y sincronizar el fork si `main` original cambia.

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
