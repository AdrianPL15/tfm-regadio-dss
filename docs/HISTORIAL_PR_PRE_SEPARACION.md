# Historial de pull requests previo a la separación del fork

El 25/10/2026 se registró este resumen antes de convertir `AdrianPL15/tfm-regadio-dss` en repositorio independiente. GitHub advierte que al salir de la red de forks se eliminan los metadatos de pull requests; los commits Git se conservan. Este archivo preserva la secuencia y el propósito de los cambios, no las conversaciones de revisión completas.

| PR | Cambio | Autor | Fusión (UTC) | Commit de fusión |
|---:|---|---|---|---|
| 1 | docs: publicar enlace de la demo Streamlit | AdrianPL15 | 2026-10-23T07:29:24Z | `0f7e998159b7f01b104ae542ce104d1c74dcf4f9` |
| 2 | Añadir maíz y algodón como casos SiAR de la demo | AdrianPL15 | 2026-10-23T11:22:41Z | `265d4092acfc68935290d7ec06f20a6c92f9dfca` |
| 3 | Documentar verificación pública de la demo multicaso | AdrianPL15 | 2026-10-23T11:24:41Z | `1fb7deceb2aba37c98d8d94466b31b2bffe459a8` |
| 4 | Integrar previsiones AEMET y escenarios de lluvia en el DSS | AdrianPL15 | 2026-10-23T12:55:20Z | `01c35f25657034b4977eb46b768642851af0c68b` |
| 5 | Aclarar configuración de la clave AEMET en Streamlit | AdrianPL15 | 2026-10-23T12:58:03Z | `a48ed7d2f14d0cb00172d56cf312be9b7698579e` |
| 6 | Actualizar campañas SiAR 2026 y demo AEMET para mañana | AdrianPL15 | 2026-10-23T17:23:29Z | `24f61e4a4ca46abe6a6c5310f248fee46e8a5782` |
| 7 | Reconstruir Streamlit tras actualizar las campañas | AdrianPL15 | 2026-10-23T17:25:20Z | `4b4a84256dee076aad913e58d8fd536f0d66e76c` |
| 8 | Mostrar panorama de siete días y aclarar la dosis de riego | AdrianPL15 | 2026-10-23T17:38:48Z | `4a9cd634b4501acd521f8a65244c5429802c6c72` |
| 9 | Unificar consulta SiAR y AEMET en el botón de recomendación | AdrianPL15 | 2026-10-23T18:03:14Z | `6a8adea169ba294d80db2e98d1c14bc78d5f4267` |
| 10 | Añadir tres cultivos en ciclo en regiones distintas a la demo | AdrianPL15 | 2026-10-23T18:18:22Z | `dc3711d859714bdf5025cb86e03555a0028074a6` |
| 11 | Simplificar la demo de riego y destacar la dosis | AdrianPL15 | 2026-10-23T18:32:43Z | `da0f35a9d0561d768fbafafee4664fd44bccb5c4` |
| 12 | Aclarar la etiqueta del horizonte histórico | AdrianPL15 | 2026-10-23T18:33:50Z | `b7b7bf385c866a559797cc0143163ac6fe2b7107` |
| 13 | Pulir título de horizonte de riego | AdrianPL15 | 2026-10-23T18:34:42Z | `b991bd9169cee46f7b37c24abc5b01f366810e5c` |

## Contexto de cada cambio

### PR 1: docs: publicar enlace de la demo Streamlit

La demo pública ya está desplegada desde el main de este fork: https://tfm-regadio-dss-adrianpl15.streamlit.app/

Se añade el enlace al README y se actualizan las guías y el estado del TFM. Verificado sin sesión de Streamlit: carga del caso inicial (39,0 mm netos, 43,3 mm brutos, 649 m³), cambio a aspersión (52,0 mm brutos) y límite de dotación de 20 mm con advertencia. Queda pendiente abrir y revisar el CSV descargado e incorporar el enlace al anexo del Word/PDF final.

### PR 2: Añadir maíz y algodón como casos SiAR de la demo

Amplía la demo Streamlit con selectores de comunidad, provincia, cultivo y estación para tres combinaciones SiAR verificadas. Incorpora los CSV oficiales de maíz Z06 (Zaragoza) y algodón BA08 (Badajoz), metadatos y documentación del alcance. Mantiene las métricas de evaluación circunscritas al piloto de pimiento. Verificación: 64 pruebas automáticas y prueba local de la interfaz en los tres casos sin excepciones.

### PR 3: Documentar verificación pública de la demo multicaso

Actualiza la guía de despliegue tras comprobar en el enlace público los casos de maíz Z06 y algodón BA08 con los valores esperados.

### PR 4: Integrar previsiones AEMET y escenarios de lluvia en el DSS

Incluye la evaluación previa de maíz y algodón y añade la integración AEMET al DSS.

- Consulta municipal diaria/horaria y preserva municipio, emisión, probabilidad, mm y cobertura.
- Escenario de lluvia condicional y explícitamente hipotético para la demo retrospectiva, sin mezclar pronósticos de 2026 con SiAR 2025.
- Archivado local de emisiones y unión temporal segura para futuros modelos; actualmente no hay solapamiento para entrenar con AEMET.
- Actualiza documentación, dependencias de Streamlit y 76 pruebas automatizadas.

Verificación local: 76/76 pruebas, app Streamlit sin excepciones, escenario manual cambia dosis 43,3→38,9 mm y consulta AEMET devuelve 7 días sin cambiar la dosis histórica. Para habilitar el botón AEMET en Community Cloud hace falta configurar `AEMET_API_KEY` como secreto de la app; no se publica en GitHub.

### PR 5: Aclarar configuración de la clave AEMET en Streamlit

Corrige el aviso del botón AEMET cuando falta la clave: distingue entre `.env` local y los secretos de Streamlit Community Cloud. Verificado con 7 pruebas del cliente AEMET.

### PR 6: Actualizar campañas SiAR 2026 y demo AEMET para mañana

Incorpora CSV oficiales de 2026 para pimiento/coliflor AL01, maíz Z06 y algodón BA08; mantiene evaluaciones 2025 separadas. La demo ofrece estimación de mañana solo para coliflor, cultivo en ciclo, con Kc futuro explícitamente proyectado y predicción AEMET actual condicionada a cobertura horaria y fracción aprovechable hipotética. Corrige el identificador interno de AEMET en Ejea, documenta procedencia y límites, y añade pruebas. Verificación local: 80 tests y arranque de Streamlit para los tres lugares.

### PR 7: Reconstruir Streamlit tras actualizar las campañas

El proceso público reutilizó el módulo Python de configuración antiguo después de la fusión y falló al leer campaign_year. Este cambio en el fichero de dependencias solicita una reconstrucción del despliegue sin alterar las versiones de bibliotecas.

### PR 8: Mostrar panorama de siete días y aclarar la dosis de riego

La demo destaca la dosis del primer día y ofrece por defecto un panorama provisional de siete días. Explica la equivalencia 1 mm = 1 L/m² = 10 m³/ha y calcula el volumen para la superficie indicada. Separa el acumulado de la dosis diaria, avisa cuando faltan días calculables y aclara que AEMET se consulta de nuevo con el botón mientras el CSV SiAR no se actualiza automáticamente. Incluye documentación y prueba de interfaz. Verificación local: 81 pruebas correctas.

### PR 9: Unificar consulta SiAR y AEMET en el botón de recomendación

La demo incorpora «Actualizar fuentes y generar recomendación»: al pulsarlo consulta el CSV SiAR del cultivo/estación 2026 seleccionado, comprueba que no cambien fechas ya versionadas y usa las jornadas nuevas en memoria; después consulta AEMET si el cultivo sigue en campaña. Si SiAR falla, se avisa y se conserva la instantánea del repositorio; si AEMET falla, se muestra la dosis base. No se publican datos ni claves desde la app. También se incluye como respaldo una tarea diaria de GitHub que propone actualizar los CSV versionados mediante PR, sin fusión automática. Verificado contra SiAR (0 jornadas nuevas al 23/10/2026) y 88 pruebas.

### PR 10: Añadir tres cultivos en ciclo en regiones distintas a la demo

Conserva los casos históricos y añade CSV oficiales SiAR 2026 de alfalfa Z06 (Zaragoza) y alcachofa BA08 (Badajoz), que junto con coliflor AL01 (Almería) tienen Kc positivo y datos recientes el 23/10. AEMET devuelve previsión para los tres municipios. La app preselecciona un cultivo en ciclo cuando existe y avisa «No hay predicción actual» para cultivos fuera de ciclo o con datos insuficientes; la dosis histórica queda etiquetada como ejemplo. El actualizador SiAR contempla los seis casos. Estos dos casos amplían la demo del motor de reglas, no reentrenan los modelos de 2025. 89 pruebas pasan y los seis CSV se comprobaron contra SiAR sin diferencias.

### PR 11: Simplificar la demo de riego y destacar la dosis

Reordena la interfaz de Streamlit para mostrar primero el cultivo y la dosis diaria en L/m², el volumen para la parcela y el panorama orientativo. Desplaza la tabla AEMET, el fundamento y el detalle técnico a secciones desplegables al final. No modifica el motor de cálculo. Verificación local: compilación correcta y 22 pruebas del motor/demostración superadas. Las pruebas de interfaz AppTest quedan pendientes de ejecución completa por bloqueo del runner local.

### PR 12: Aclarar la etiqueta del horizonte histórico

En los cultivos fuera de ciclo, sustituye «Próximos días» por «Periodo histórico» para evitar presentar una simulación pasada como previsión actual.

### PR 13: Pulir título de horizonte de riego

Ajuste de redacción para mostrar «Próximos 7 días» o «Periodo histórico de 7 días», sin redundancia.
