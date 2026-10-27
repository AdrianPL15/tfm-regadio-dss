# Aplicación de los principios FAIR

El proyecto aplica los principios FAIR de forma proporcional al alcance del
piloto. FAIR no significa que todos los datos deban ser abiertos: exige que los
activos sean encontrables, accesibles bajo condiciones explícitas,
interoperables y reutilizables.

| Principio | Evidencia actual | Siguiente control antes de publicar con DOI |
|---|---|---|
| Encontrable | Repositorio público, nombres estables, `CITATION.cff` y ficha del conjunto | Crear una versión etiquetada y depositarla en Zenodo |
| Accesible | Código, muestras, resultados y memoria disponibles por HTTPS | Documentar qué raw no se distribuye y cómo solicitarlo de nuevo |
| Interoperable | CSV y JSON, fechas ISO 8601, unidades explícitas y claves de estación, cultivo y fecha | Exportar tablas analíticas a Parquet con esquema versionado |
| Reutilizable | Licencia MIT para activos propios, procedencia, diccionario y comandos de reproducción | Verificar por escrito las condiciones de redistribución de SiAR y AEMET |

## Paquete mínimo de una versión académica

1. Etiqueta inmutable en Git y notas de versión.
2. Código, memoria, requisitos y pruebas asociados a la misma revisión.
3. `CITATION.cff`, licencia, ficha del conjunto y condiciones de los datos.
4. Diccionario de variables, unidades, claves y reglas de calidad.
5. Identificación de fuente, fecha de extracción y transformación aplicada.
6. DOI de Zenodo cuando la versión y los derechos de redistribución estén
   comprobados.

La publicación no debe incluir tokens, secretos ni información de usuarios. Los
datos originales de terceros no se relicencian mediante la licencia del código.
