# 6.1. Cumplimiento de objetivos y aportaciones

## 6.1.1. Valoración de los objetivos

El objetivo general del trabajo era diseñar, implementar y evaluar un sistema
inteligente de apoyo a la decisión que integrara datos meteorológicos,
ambientales, agronómicos e hidrológicos, estimara las necesidades de riego y
las transformara en recomendaciones operativas, trazables y comprensibles. Al
término del proyecto puede afirmarse que el objetivo se ha alcanzado como
prueba de concepto y dentro de un caso acotado. El repositorio contiene una
cadena completa y reproducible que parte de las APIs públicas de SiAR y AEMET y
termina en una recomendación diaria y semanal, explicada y evaluada frente a
una referencia oficial. Esa afirmación tiene un límite preciso: se ha
demostrado con una estación, un cultivo y una campaña, y frente a una necesidad
calculada, no frente al riego aplicado ni a la respuesta del cultivo. La
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
| Realizar el análisis exploratorio y construir variables derivadas | Apartado 4.2; catálogo de 88 variables | Parcial | Cobertura, calidad y disponibilidad temporal de cada variable caracterizadas. Con un cultivo, una localización y sin datos de disponibilidad de agua, solo puede estudiarse la relación entre meteorología, fase del cultivo y demanda. |
| Desarrollar y comparar modelos predictivos | Apartado 4.3; seis enfoques con validación temporal | Cumplido | Comparación con métricas objetivas y prueba reservada. Ningún algoritmo de aprendizaje supera de forma estable a la persistencia. |
| Diseñar una lógica de recomendación sobre cantidad y momento de riego | Apartado 5.1; motor con reglas R1 a R10 | Parcial | Resuelve cuánto regar a escala diaria y semanal, con eficiencia y dotación. El momento solo se trata mediante avisos de aplazamiento: sin balance hídrico del suelo no puede decidirse cuándo regar. |
| Implementar un prototipo de aplicación o panel de visualización | Apartado 5.2; aplicación en Streamlit y línea de comandos | Cumplido | Aplicación funcional y reproducible. Cultivo y estación fijados en el caso piloto; Power BI o Tableau sustituidos de forma justificada; sin evaluación con usuarios. |
| Evaluar el funcionamiento integral del sistema | Apartado 5.3; validación, 13 escenarios y 55 pruebas automáticas | Cumplido | Comparación con la referencia SiAR y con la persistencia, error por horizonte, coherencia semanal y robustez. Validación técnica, no externa ni de campo. |

El balance es de cuatro objetivos cumplidos y tres parciales, y los tres
parciales comparten una misma causa. En ninguno de ellos la carencia es
metodológica ni de implementación: lo que falta es información a escala de
parcela o de recurso hídrico, como la disponibilidad real de agua, las
propiedades del suelo o los riegos aplicados. El sistema está preparado para
incorporarla, puesto que admite como entradas la eficiencia medida, la dotación
y una ET0 prevista, pero no puede suplirla. Esta constatación ordena las líneas
de mejora del apartado 6.3.

## 6.1.2. Aportaciones del trabajo

La aportación principal es un resultado empírico que no estaba previsto en el
anteproyecto. Para anticipar la necesidad de riego de un cultivo con calendario
definido, separar la estimación en sus dos componentes resulta más eficaz que
aumentar la complejidad del modelo. Uno de ellos, la demanda atmosférica, es
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
desde la persistencia hasta XGBoost, se compararon con las mismas variables,
los mismos cortes temporales y una prueba reservada que no intervino en la
selección, y ninguno de los cinco algoritmos de aprendizaje superó de forma
estable a la referencia más simple. Este resultado no resta valor al trabajo.
Es coherente con lo expuesto en el apartado 2.2: con un único ciclo de 148
observaciones y una necesidad neta dominada por el calendario del cultivo (su
correlación con el Kc es de 0,93), la complejidad añadida no encuentra señal
que aprender. Su fiabilidad descansa en dos decisiones documentadas. La primera
fue excluir la ET0, la ETc y la precipitación efectiva del mismo día, que
habrían permitido reconstruir el objetivo de forma algebraica y producir
métricas aparentemente excelentes. La segunda, seleccionar el enfoque antes de
consultar la prueba final. Leídos conjuntamente, los capítulos 4 y 5 respaldan
el planteamiento híbrido del apartado 2.3: con pocos datos, el conocimiento
agronómico explícito aporta más que el algoritmo, y el aprendizaje automático
encuentra su lugar como corrección de una referencia física, no como sustituto
de ella.

La tercera aportación es de diseño. El motor convierte la incertidumbre en
parte de la salida en lugar de ocultarla. Cada recomendación indica el método
que la produjo, las reglas aplicadas, el último dato observado, un nivel de
confianza y el error esperado para su día del horizonte, y el sistema prefiere
no emitir una dosis antes que ofrecer una cifra sin fundamento. Ninguna
ausencia se convierte en cero y ninguna dosis resulta negativa. Las pruebas
automáticas verifican, además, que la planificación no cambia cuando se alteran
los datos posteriores a la fecha de emisión, que es la garantía formal de que
el sistema no utiliza información futura.

La cuarta aportación es la reproducibilidad. Todas las cifras, tablas y figuras
de los capítulos 4 y 5 se regeneran con un comando desde el repositorio, las
cincuenta y cinco pruebas automáticas se superan en un entorno limpio y el
sistema de recomendación puede ejecutarse sin credenciales a partir del CSV
oficial versionado. La correspondencia entre la memoria y el código no es, por
tanto, una declaración, sino algo que cualquier lector puede comprobar.
