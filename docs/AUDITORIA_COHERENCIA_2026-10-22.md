# Auditoría de coherencia de la versión para el tutor

Esta nota contrasta las propuestas de la revisión externa de octubre de 2026
con el código, las tablas generadas y la memoria. No convierte una prueba de
concepto en una validación agronómica de campo.

## Correcciones incorporadas

| Asunto | Resolución |
|---|---|
| Alcance del DSS | Objetivo, resumen y capítulos 1, 4, 5 y 6 distinguen visión multicultivo de piloto fijo en AL01/pimiento. El capítulo 5 se denomina «Sistema de recomendación». |
| Fuentes | SiAR histórico y CSV de necesidades sustentan la evaluación; AEMET 2026 solo prueba extracción y normalización; MITECO queda fuera del motor. |
| Prueba temporal | El periodo 8–30/09/2025 es prueba para la comparación del capítulo 4, pero se reutiliza después al analizar el motor ET0×Kc. No se presenta este segundo análisis como validación independiente. |
| Modelos | Se explica por qué la tabla tiene 88 columnas y el experimento predictivo usa nueve variables; también los tamaños de los tres cortes temporales. La comparación agronómica ET0 reciente × Kc queda en el capítulo 5, separada de los seis enfoques originales. |
| Línea base y horizontes | Se conserva la persistencia por continuidad del experimento y se añade como referencia la ventana ET0 de un día. Se informa de que el DSS pierde frente a la persistencia en el día 7 del tramo de prueba. |
| Cifras | Se aclaran 124 frente a 125 filas, la diferente fecha de arranque de las tablas 5.4 y 5.5, las dos definiciones de MAE semanal y que 531,05 mm suman 148 días válidos, no la campaña completa. |
| Confianza | El aviso desde el día 4 se identifica como regla prudencial de interfaz, no como umbral calibrado con los errores observados. |
| Reproducibilidad | Se versiona una instantánea acotada de tres respuestas públicas, además del CSV SiAR y sus metadatos; se exige selección explícita si hay varias estaciones/campañas. No se versionan tokens. |
| Presentación | Los pies de las figuras 3.1 y 4.1 quedan junto a sus imágenes; el gráfico 4.1 ya no atribuye a la interfaz una selección de cultivo y zona que todavía no existe. La leyenda de la figura 4.7 se separó de los datos, la tabla 5.2 queda en una página, se incorpora notación agronómica en 2.1 y se simplifica la tabla 4.1. |

## Comprobación reproducible

El 22/10/2026 se copió solo el conjunto de archivos versionados, sin `.env`,
`data/interim` ni `data/processed`. En esa copia se reconstruyeron las cuatro
tablas interim (150 SiAR clima, 150 SiAR necesidades, 7 AEMET diarias y 48
AEMET horarias), la tabla procesada (150 filas y 88 columnas), el análisis
exploratorio, la comparación de modelos y la validación del motor. Se obtuvo
MAE de persistencia de 0,120 mm/día en prueba y los 13 escenarios pasaron.
Tras incorporar los dos tests de la demo, la suite completa pasó con 61/61
pruebas. Se utilizó el entorno Python ya instalado; queda por comprobar la
instalación de dependencias desde cero en otro equipo. Los comandos se indican
en [REPRODUCCION_PILOTO.md](REPRODUCCION_PILOTO.md).

El 23/10/2026 se repitieron las 61 pruebas con un directorio temporal dentro
del espacio de trabajo (61/61 correctas) y se ejecutó la prueba local de la
interfaz Streamlit: sin excepciones, con título y cuatro indicadores visibles.
Esta comprobación no equivale a un despliegue público ni a una prueba manual
en navegador. La memoria revisada se exportó de nuevo a PDF (84 páginas) y se
comprobó visualmente la disposición de las secciones 3.1 y 4.1.

## Límites que no se deben esconder

- No existe un *hold-out* independiente para el método ET0×Kc tras la
  reutilización de septiembre. Una campaña posterior o una estación distinta
  permitiría una prueba externa, pero no debe simularse ni afirmarse sin datos.
- El CSV de SiAR identifica «Pimiento», no acredita por sí solo que sea un
  cultivo al aire libre. La configuración se trata como hipótesis del piloto
  hasta incorporar la fuente específica que aportará el equipo.
- No hay observaciones de humedad de suelo, riego aplicado, rendimiento ni
  ahorro real. La dosis y el volumen calculados son orientativos.
- La interfaz publicada todavía no permite escoger ubicación ni cultivo, y
  no hay enlace público permanente verificado para la demo Streamlit.
- El fichero general `requirements.txt` no está fijado por versión. Se añadió
  `requirements-piloto.txt` con las versiones principales usadas en la prueba,
  pero aún falta verificar su instalación desde cero en otro equipo.

## Fuentes oficiales contrastadas

Se comprobó que los porcentajes de contexto **70/40/20** están recogidos por
[FAO AQUASTAT](https://www.fao.org/aquastat/en/activities/prev-projects/cws-phase1/)
y que la relación española **22/65** figura en el [preámbulo del Real Decreto
854/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-16583).
Las notas legales de [SiAR](https://servicio.mapa.gob.es/siarweb/avisoLegal)
y [AEMET](https://www.aemet.es/es/nota_legal) se consultaron para la
instantánea de datos públicos, con atribución expresa y sin sugerir respaldo
institucional al proyecto.
