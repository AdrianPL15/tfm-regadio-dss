# Auditoría del parche del capítulo 6

Fecha: 17 de octubre de 2026

## Alcance

Se revisaron los diez archivos del parche recibido, el Word y el PDF enviados
por el equipo, las fuentes Markdown de los capítulos afectados, el código de
ETL, modelado y DSS y los resultados versionados. El parche se aplicó a una
rama local; esta auditoría no implica que sus cambios estén en `main` ni en
GitHub.

## Comprobaciones realizadas

| Afirmación | Evidencia | Resultado |
|---|---|---|
| 148 días válidos de la campaña | CSV oficial de necesidades y evaluación 4.3 | Confirmada: 150 fechas, 148 filas completas |
| 88 variables catalogadas | `docs/data_samples/feature_catalog_4_2.csv` | Confirmada |
| Seis enfoques, cinco de aprendizaje | `src/models/train_evaluate.py` y evaluación 4.3 | Confirmada; la persistencia utiliza el último valor, no las nueve variables de los otros modelos |
| 13 escenarios de validación | `docs/data_samples/dss_scenarios_5_3.csv` | Confirmada |
| 55 pruebas automáticas | `python -m unittest discover -s tests` | 55 ejecutadas correctamente en el entorno local |
| 2,51 mm de precipitación efectiva | CSV oficial de necesidades de 2025 | Confirmada sobre las 148 filas válidas |
| ETL parametrizada para cualquier cultivo | `src/data/transform_interim.py` | No confirmada: se selecciona el CSV de necesidades más recientemente modificado |
| Todas las salidas se regeneran con un comando | README y módulos del proyecto | No confirmada: se utilizan comandos separados por fase |

## Correcciones incorporadas tras la auditoría

1. Se sustituyó la hoja de estado desactualizada, que seguía describiendo los
   capítulos 5 y 6 como vacíos, por un diagnóstico vigente y una lista de
   tareas finales.
2. Se corrigió el README para separar la visión del producto del piloto fijo,
   añadir los pasos de ingeniería de variables y análisis exploratorio que
   faltaban y enlazar el capítulo 6.
3. Se matizó el capítulo 6: los objetivos parciales no tienen una sola causa;
   los modelos de aprendizaje y la persistencia no usan las mismas variables;
   los datos antiguos reducen la confianza pero no siempre impiden emitir una
   dosis; y la reproducción requiere varios comandos y dependencias.
4. Se describió con precisión la ampliación multicultivo pendiente: el CSV
   agronómico se obtiene por la web de SiAR y su selección explícita aún debe
   implementarse.
5. Se precisó la propuesta de previsión futura: el pronóstico de necesidades
   netas de SiAR depende de AEMET, cubre seis días según su manual y no
   constituye una validación independiente frente a otra salida de SiAR.
   Referencia oficial: https://servicio.mapa.gob.es/siarweb/documentos/manuales/ManualUsoWebSiAR.pdf
6. Se trasladaron las correcciones al Word de la memoria y se añadió la
   referencia bibliográfica del manual de SiAR.

## Comprobación visual y límites pendientes

El Word auditado se exportó temporalmente a PDF y se revisaron sus 79 páginas
mediante imágenes de contacto, además de las páginas modificadas a tamaño de
lectura. No se observaron páginas en blanco ni texto cortado. La Tabla 6.2
continúa entre dos páginas con su encabezado repetido; es legible, aunque aún
puede pulirse la paginación en la maquetación final. El PDF recibido con el
parche es anterior a estas correcciones y ya no coincide con el Word auditado.

Antes de la entrega siguen pendientes la portada definitiva, resumen, abstract,
índice, listas, anexos, cotejo bibliográfico completo, confirmación agronómica
del calendario y `Kc` para pimiento al aire libre, y generación y revisión del
PDF final. El piloto no permite afirmar ahorro real de agua, elección óptima
del momento de riego ni generalización a otros cultivos y estaciones.
