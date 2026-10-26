# Prueba funcional final de la aplicación Streamlit

**Fecha de ejecución:** 25 de octubre de 2026  
**Aplicación:** https://tfm-regadio-dss-adrianpl15.streamlit.app/  
**Objetivo:** comprobar desde la aplicación pública la actualización de fuentes, la generación de recomendaciones, la comunicación con AEMET, el tratamiento de cultivos fuera de ciclo, el descuento por lluvia y la disponibilidad del CSV.

## Resultado general

La aplicación completó el recorrido funcional sin errores visibles. SiAR incorporó dos jornadas nuevas y dejó como última observación el 24 de octubre de 2026. AEMET respondió en los tres casos activos, aunque en la consulta realizada no aportó una cantidad de precipitación numérica utilizable; la aplicación lo indicó expresamente y no interpretó la ausencia de cantidad como lluvia cero.

## Casos comprobados

| Comunidad | Provincia | Cultivo | Estación | Resultado para 25/10/2026 | Horizonte de 7 días | Estado |
|---|---|---|---|---:|---:|---|
| Andalucía | Almería | Coliflor | AL01 La Mojonera | 2,3 L/m²; 35 m³ para 1,50 ha | 16,4 L/m²; 246 m³; 7 de 7 días | Correcto |
| Aragón | Zaragoza | Alfalfa | Z06 Ejea de los Caballeros | 1,9 L/m²; 29 m³ para 1,50 ha | 13,5 L/m²; 203 m³; 7 de 7 días | Correcto |
| Extremadura | Badajoz | Alcachofa | BA08 Don Benito | 2,4 L/m²; 35 m³ para 1,50 ha | 16,5 L/m²; 248 m³; 7 de 7 días | Correcto |
| Andalucía | Almería | Pimiento | AL01 La Mojonera | No genera una recomendación actual porque SiAR lo sitúa fuera del periodo de ciclo | Presenta el último ejemplo histórico sin confundirlo con una recomendación actual | Correcto |

## Integración de fuentes

- SiAR comunicó dos jornadas nuevas y una última observación de 24/10/2026.
- AEMET devolvió respuesta para los casos activos.
- Al no existir milímetros numéricos aprovechables para la fecha, la dosis no descontó precipitación y mostró una advertencia comprensible.
- La interfaz distingue la recomendación de hoy de la revisión histórica.

## Comprobación del descuento por lluvia

En el caso de alcachofa se activó el escenario manual, identificado por la propia aplicación como hipotético y no atribuible a AEMET. Con 8 mm de lluvia y una fracción aprovechable del 50 %, la lluvia efectiva simulada fue 4 mm. Como superaba la necesidad calculada del cultivo, la dosis del primer día pasó de 2,4 L/m² a 0,0 L/m² y el volumen pasó de 35 m³ a 0 m³. El comportamiento confirma que el motor descuenta la lluvia y evita producir dosis negativas.

## Descarga CSV

El control `Descargar recomendación (CSV)` permaneció habilitado en los casos calculables y respondió al clic. Se inspeccionó además un CSV generado por la aplicación para coliflor AL01: contiene siete filas, del 25 al 31 de octubre de 2026, y 24 columnas de trazabilidad, incluidas Kc, ET0 utilizada, precipitación prevista, necesidad neta, método, dosis bruta, volumen, confianza, reglas, advertencias, última observación y archivo fuente.

## Conclusión

La aplicación pública cumple el recorrido que se pretende mostrar en la defensa: selección de zona y cultivo, actualización de SiAR, consulta de AEMET, recomendación diaria, orientación semanal, explicación de unidades, tratamiento explícito de la incertidumbre, aviso de cultivo fuera de ciclo y exportación estructurada. La lluvia AEMET no pudo validarse con una cantidad real positiva en esta ejecución porque la respuesta no incluía milímetros utilizables; la regla de descuento quedó comprobada mediante el escenario hipotético claramente etiquetado.
