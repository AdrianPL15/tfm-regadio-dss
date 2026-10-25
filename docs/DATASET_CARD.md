# Ficha de los datos del piloto

## Finalidad

Los datos permiten reproducir la extracción, preparación, comparación de
modelos y recomendación orientativa del DSS de riego. La variable objetivo es
la necesidad neta calculada por SiAR; no representa el riego realmente aplicado
ni una dosis validada en parcela.

## Fuentes y cobertura

| Fuente | Contenido | Cobertura utilizada | Procedencia |
|---|---|---|---|
| SiAR API | Meteorología observada por estación | Periodos solicitados por cultivo y campaña | Ministerio de Agricultura, Pesca y Alimentación |
| SiAR web | Kc, ET0, ETc, precipitación efectiva y necesidad neta | CSV por cultivo, estación y periodo | Calculadora de necesidades hídricas de SiAR |
| AEMET OpenData | Predicción municipal de lluvia | Consulta operativa en la aplicación | Agencia Estatal de Meteorología |

El piloto ampliado conserva nueve CSV oficiales en seis combinaciones de
cultivo y estación. Las campañas disponibles no tienen la misma longitud y
algunos cultivos solo aportan una campaña parcial de 2026.

## Niveles del dato

| Nivel | Ubicación | Uso |
|---|---|---|
| Externo | `data/external/` | CSV descargados y metadatos, sin transformar |
| Raw | `data/raw/` | Respuestas originales de las API, normalmente excluidas de Git por volumen o credenciales |
| Interim | `data/interim/` | Datos normalizados y controles de calidad |
| Processed | `data/processed/` | Tablas analíticas y predictores temporales |
| Muestras y resultados | `docs/data_samples/` | Evidencias pequeñas incluidas en el repositorio |

El diccionario funcional de variables y sus unidades se encuentra en
`docs/FUENTE_DATOS_SIAR.md`, `docs/FUENTE_DATOS_AEMET.md` y
`docs/ESTRATEGIA_DATOS_DSS.md`.

## Identificadores y trazabilidad

La clave lógica principal combina estación, cultivo y fecha. Los archivos
procesados mantienen columnas de fuente, archivo de origen, estado de calidad y
fecha de ingesta. Los metadatos JSON asociados a cada CSV identifican el caso y
la campaña. Las transformaciones se regeneran mediante los módulos de `src/`.

## Calidad y exclusiones

- Las fechas no parseables y las claves duplicadas se consideran errores.
- Los días fuera del ciclo, identificados por Kc igual a cero, no se usan para
  evaluar la necesidad activa.
- Los ausentes no se convierten automáticamente en cero.
- Los retardos se calculan respetando el calendario y sin trasladar valores
  entre campañas.
- La evaluación reserva bloques temporales posteriores y evita variables del
  mismo día que producirían fuga de información.

## Limitaciones y usos inadecuados

Estos datos no deben emplearse para prescribir un riego sin revisión agronómica.
No contienen de forma general humedad del suelo, riego aplicado, drenaje,
rendimiento, estrés del cultivo ni validación con agricultores. Tampoco permiten
demostrar ahorro de agua o impacto económico. Las previsiones AEMET consumidas
en directo no disponen todavía de un archivo histórico de emisiones equivalente
al histórico SiAR usado en la evaluación.

## Reutilización y citación

El código y la documentación originales se distribuyen bajo licencia MIT. Los
datos de terceros mantienen sus condiciones de origen, descritas en
`DATA_LICENSE.md`. La forma recomendada de citar el proyecto figura en
`CITATION.cff`. Una futura publicación con DOI deberá incluir una versión
etiquetada, esta ficha, el diccionario de variables, la procedencia y los
controles de calidad, sin redistribuir datos cuya licencia no lo permita.
