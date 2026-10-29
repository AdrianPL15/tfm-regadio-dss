# 6.1. Cumplimiento de objetivos y aportaciones

## 6.1.1. Valoración de los objetivos

El objetivo general del trabajo era diseñar, implementar y evaluar un sistema
inteligente de apoyo a la decisión que integrara datos meteorológicos,
ambientales, agronómicos e hidrológicos, estimara las necesidades de riego y
las transformara en recomendaciones operativas, trazables y comprensibles. Al
término del proyecto puede afirmarse que el objetivo se ha alcanzado como
prueba de concepto y dentro de un caso acotado. El repositorio contiene una
cadena reproducible que parte de observaciones y necesidades de SiAR y termina
en una recomendación diaria y semanal, explicada y evaluada frente a una
referencia oficial. La app consulta AEMET actual para condicionar la dosis de
mañana cuando la emisión y la cantidad de lluvia son utilizables; esa previsión
no forma parte del entrenamiento ni de la evaluación retrospectiva de 2025.
El experimento predictivo ampliado reúne nueve CSV en seis casos de tres
estaciones, mientras que la validación integral del DSS sigue centrada en
pimiento AL01 durante 2025. En ambos casos se contrasta una necesidad calculada,
no el riego aplicado ni la respuesta del cultivo. La
dimensión hidrológica del objetivo, además, se ha resuelto mediante una
dotación que introduce el usuario y no mediante datos oficiales de
disponibilidad de agua.

Para valorar los objetivos específicos se ha seguido un criterio
deliberadamente estricto. Un objetivo se considera cumplido cuando existe un
resultado implementado, reproducible desde el repositorio y evaluado en esta
memoria. Se considera parcial cuando alguna parte de su formulación en el
apartado 1.2 no se ha abordado o se ha sustituido por una alternativa más
limitada, aunque la sustitución esté justificada. La Tabla 6.1 recoge la
valoración.

**Tabla 6.1. Grado de cumplimiento de los objetivos específicos.**

| Objetivo específico (apartado 1.2) | Evidencia principal | Grado | Alcance y desviaciones |
|---|---|---|---|
| Identificar y documentar las fuentes y variables del problema | Apartado 3.1; inventarios de SiAR y AEMET | Parcial | SiAR y AEMET documentadas e integradas. Los datos hidrológicos del MITECO se analizaron y se descartaron por su escala de embalse y cuenca (apartado 5.1.4). |
| Diseñar un flujo de datos reproducible con calidad y trazabilidad | Apartado 4.1; capas raw, interim y processed | Cumplido | Controles de calidad que no destruyen el dato original y procedencia hasta el archivo raw. El almacenamiento es local; la evolución prioriza ingesta programada, almacenamiento de objetos y Parquet, con persistencia relacional para la operación (apartado 3.2.2). |
| Realizar el análisis exploratorio y construir variables derivadas | Apartado 4.2; catálogo de 88 variables | Parcial | El análisis profundo se realizó para el piloto de pimiento AL01. La ampliación añade otros cultivos y campañas, pero no datos de disponibilidad de agua por parcela. |
| Desarrollar y comparar modelos predictivos | Apartado 4.3; seis enfoques con validación temporal y ampliación a seis casos | Cumplido | Comparación con métricas objetivas y prueba reservada. Ningún algoritmo de aprendizaje supera de forma estable a la persistencia en todos los casos; se documentan diferencias por cultivo. |
| Diseñar una lógica de recomendación sobre cantidad y momento de riego | Apartado 5.1; motor con reglas R1 a R10 | Parcial | Resuelve cuánto regar a escala diaria y semanal, con eficiencia y dotación. El momento solo se trata mediante avisos de aplazamiento: sin balance hídrico del suelo no puede decidirse cuándo regar. |
| Implementar un prototipo de aplicación o panel de visualización | Apartado 5.2; aplicación pública en Streamlit y línea de comandos | Cumplido | Permite seleccionar entre nueve CSV verificados, distribuidos en seis combinaciones de cultivo y estación. Power BI o Tableau se sustituyeron de forma justificada; falta evaluación con usuarios. |
| Evaluar el funcionamiento integral del sistema | Apartado 5.3; validación, 13 escenarios y pruebas automáticas | Cumplido | Comparación con la referencia SiAR y con la persistencia, error por horizonte, coherencia semanal y robustez en el piloto de 2025. La evaluación de la consulta actual con AEMET y la validación de campo siguen pendientes. |

El balance es de cuatro objetivos cumplidos y tres parciales. Las desviaciones
no tienen una única causa: faltan datos hidrológicos y de parcela, más campañas
para comprobar la generalización y, para decidir el momento del riego, un
balance hídrico del suelo. El motor ya admite como entradas la eficiencia, la
dotación y una ET0 prevista, pero incorporar propiedades del suelo y riegos
aplicados requiere ampliar tanto los datos como la lógica de decisión. Estas
limitaciones ordenan las líneas de mejora del apartado 6.3.

## 6.1.2. Aportaciones del trabajo

La aportación principal es una arquitectura híbrida que asigna funciones
distintas a la predicción y al conocimiento agronómico. La vía operativa
preferente predice ET0 mediante Ridge multianual para `h=1…9` y combina cada
predicción con el Kc conocido de la fecha; la media de siete días permanece
como respaldo controlado. En la validación con origen rodante, 63 de 81
intervalos bootstrap favorecieron a Ridge frente al respaldo y 18 fueron no
concluyentes. Esta evidencia es retrospectiva: hasta reunir 30 casos
prospectivos pareados, Ridge se etiqueta como provisional y no se afirma una
mejora operativa consolidada.

La segunda aportación es una comparación temporal reproducible y una
interpretación honesta de resultados diferentes. En el piloto de una sola
campaña, cinco algoritmos de aprendizaje no superaron de forma estable a
persistencia. En cambio, la ampliación multianual de ET0 sí mostró una mejora
consistente frente a la media móvil de siete días. La evaluación física del
capítulo 5 reutiliza fechas del piloto y valida el respaldo `ET0 reciente ×
Kc`, no la vía Ridge completa. En su prueba reservada a un día, ese respaldo
redujo el MAE un 25 %, pero la diferencia absoluta fue 0,029 mm/día y su
intervalo bootstrap del 95 % [0,002; 0,067] quedó próximo a cero; por ello se
presenta como evidencia interna, no como generalización agronómica.

La tercera aportación es de diseño. El motor hace visibles sus limitaciones en
la salida. Cada recomendación indica el método que la produjo, las reglas
aplicadas, el último dato observado, un nivel de confianza y, cuando está
disponible el informe de validación, el error medio para su día del horizonte.
Si falta información imprescindible no se emite una dosis; si los datos son
antiguos, se conserva la estimación con un aviso y confianza baja. Las filas
sin estimación permanecen ausentes, no se convierten en dosis cero, y ninguna
dosis emitida resulta negativa. Las pruebas
automáticas verifican, además, que la planificación no cambia cuando se alteran
los datos posteriores a la fecha de emisión, que es la garantía formal de que
el sistema no utiliza información futura.

La cuarta aportación es la reproducibilidad. El repositorio conserva los datos
del piloto, los informes de evaluación y los módulos que generan las
principales evidencias cuantitativas y visualizaciones de los capítulos 4 y 5;
el README documenta los comandos separados
para ejecutar cada fase. Las 150 pruebas automáticas se han
ejecutado correctamente en el entorno local del proyecto y el motor de
recomendación puede utilizar el CSV oficial versionado sin nuevas credenciales.
Así, el lector puede comprobar la correspondencia entre la memoria y el código,
siempre que disponga de las dependencias indicadas.
