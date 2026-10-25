# Revisión cruzada de memoria, repositorio y demo

Fecha de comprobación: 25 de octubre de 2026.

## Qué se ha contrastado

| Tema | Memoria de entrega | Código y evidencia | Demo pública |
|---|---|---|---|
| Alcance | Piloto de pimiento AL01 en 2025; ampliación a seis combinaciones de cultivo y estación | `src/dss/config.py` declara nueve instantáneas CSV de seis combinaciones | El selector recorre las combinaciones verificadas, no cualquier cultivo y zona de España |
| Fecha de consulta | «Recomendación (hoy o mañana)» y «Revisión histórica (día cerrado)» | `src/dss/app_streamlit.py` propone hoy para un cultivo activo con SiAR reciente; `src/dss/live_calendar.py` proyecta Kc dentro del mes declarado | Verificado con coliflor AL01: el 25/10/2026 se mostró la dosis de hoy; el modo histórico retrocedió al 24/10 |
| Necesidad antes de lluvia | El modelo de ETc y la vía `ET0 reciente × Kc` se comparan por caso | `docs/data_samples/etc_model_deployment_2026.json`: la vía física conserva la dosis en cinco casos; el artefacto de algodón puede determinarla si existe observación directa y está en ciclo | Para coliflor se mostró Ridge como contraste y la estimación física como dosis |
| Lluvia AEMET | Descuento condicional de una fracción supuesta tras estimar ETc | `src/dss/aemet_forecast.py`: hoy solo horas posteriores a la consulta; mañana cobertura de 24 horas; sin mm utilizables no se descuenta | La consulta del 25/10 mostró 0,0 mm para las horas restantes. La app indica la fracción supuesta |
| Dosis de hoy | Necesidad orientativa del día completo, sin conocer riego ni lluvia ya ocurridos | El motor no lleva balance hídrico de parcela ni historial de riegos aplicados | Aviso visible antes de las métricas; si se ha regado, la cifra requiere ajuste |
| Validación | El piloto de 2025 se evaluó retrospectivamente frente a referencia SiAR | 13 escenarios documentados; las 103 pruebas automáticas pasaron el 25/10/2026 | La consulta en vivo demuestra funcionamiento, no ahorro ni precisión agronómica en campo |

## Comprobación del entregable escrito

La versión de entrega es `docs/memoria/TFM_definitivo_2026-10-25.docx` y su PDF
homónimo. El PDF tiene 85 páginas. Los índices se cotejaron contra las páginas
exportadas: sus 141 entradas se localizaron en la página indicada, sin
desfases. Se renderizaron y revisaron visualmente las 85 páginas definitivas,
sin cortes ni solapamientos. Las 34 direcciones externas del documento se
convirtieron en hipervínculos activos y se mantuvo la notación `mm/día` de forma
uniforme.

## Límites que deben mantenerse explícitos al presentar

- El CSV de pimiento de SiAR identifica el cultivo, pero no especifica el sistema
  productivo. El equipo asume cultivo al aire libre para el piloto.
- No existen registros de riego aplicado, humedad del suelo ni validación de la
  precipitación efectiva en la parcela.
- No hay un archivo histórico de emisiones AEMET alineadas con las fechas de
  2025 para medir retrospectivamente su aportación.
- El horizonte posterior al primer día es orientativo y se recalcula con nuevas
  observaciones. El séptimo día perdió frente a persistencia en el piloto.
- La suite completa de 103 pruebas pasó fuera del aislamiento local de sockets.
  `AppTest` necesita crear un canal interno de Windows; dentro de ese entorno
  aislado se bloquea antes de ejecutar la aplicación.

Antes de enviar el TFM, el equipo debe leer el PDF completo. Los resultados de
la demo varían con la hora de consulta y la
disponibilidad de SiAR y AEMET.
