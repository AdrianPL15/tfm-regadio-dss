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
| Diseñar un flujo de datos reproducible con calidad y trazabilidad | Apartado 4.1; capas raw, interim y processed | Cumplido | Controles de calidad que no destruyen el dato original y procedencia hasta el archivo raw. El almacenamiento es local; MySQL y Apache Hop quedan como arquitectura objetivo (apartado 3.2.2). |
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

La aportación principal es un resultado empírico que no estaba previsto en el
anteproyecto. En este piloto, para anticipar la necesidad de riego de un
cultivo con calendario definido, separar la estimación en sus dos componentes
resultó más eficaz que aumentar la complejidad del modelo. Uno de ellos, la
demanda atmosférica, es
incierto pero evoluciona de forma gradual; el otro, el coeficiente de cultivo,
cambia de forma brusca pero se conoce de antemano. La vía que multiplica la ET0
media de los siete días anteriores por el Kc del día objetivo reduce el MAE de
la recomendación a un día frente a la persistencia en un 7 % en desarrollo y en
un 25 % en la prueba, y el RMSE de desarrollo en un 18 %. La diferencia se
amplía con la anticipación: a siete días, en el periodo de desarrollo, el error
del sistema es de 0,48 mm frente a 0,87 mm de la persistencia, porque se
mantiene prácticamente estable a lo largo del horizonte. Donde el método se
distingue con más claridad es en los cambios de fase. El 1 de septiembre,
cuando el Kc pasa de 1,00 a 0,30, la persistencia se desvía 3,52 mm y el
sistema 0,01 mm.

La segunda aportación es un resultado negativo bien acotado. Seis enfoques,
desde la persistencia hasta XGBoost, se compararon sobre la misma variable
objetivo, los mismos cortes temporales y una prueba reservada que no intervino
en la selección. Los cinco algoritmos de aprendizaje utilizaron el conjunto de
variables definido en el apartado 4.3; la persistencia utilizó el último valor
observado. Ninguno de los algoritmos de aprendizaje superó de forma estable a
esta referencia sencilla. Este resultado no resta valor al trabajo. Es
coherente con lo expuesto en el apartado 2.2: con un único ciclo de 148
observaciones y una necesidad neta muy relacionada con el calendario del
cultivo (su correlación con el Kc es de 0,93), los modelos más complejos no
disponen de diversidad suficiente para demostrar una mejora estable. La
validez de la comparación de los seis enfoques del capítulo 4 descansa en dos decisiones documentadas. La primera
fue excluir la ET0, la ETc y la precipitación efectiva del mismo día, que
habrían permitido reconstruir el objetivo de forma algebraica y producir
métricas aparentemente excelentes. La segunda, seleccionar el enfoque antes de
consultar la prueba final. El método ET0 reciente × Kc se desarrolló y evaluó
después usando las mismas fechas de septiembre; su resultado no constituye una
validación independiente adicional. Leídos conjuntamente, los capítulos 4 y 5 respaldan
el planteamiento híbrido del apartado 2.3: con pocos datos, el conocimiento
agronómico explícito aporta más que el algoritmo, y el aprendizaje automático
encuentra su lugar como corrección de una referencia física, no como sustituto
de ella.

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
para ejecutar cada fase. Las sesenta y una pruebas automáticas se han
ejecutado correctamente en el entorno local del proyecto y el motor de
recomendación puede utilizar el CSV oficial versionado sin nuevas credenciales.
Así, el lector puede comprobar la correspondencia entre la memoria y el código,
siempre que disponga de las dependencias indicadas.
