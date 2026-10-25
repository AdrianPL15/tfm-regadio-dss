# 6.3. Mejoras y líneas futuras

Las líneas de mejora se presentan en el orden en que deberían abordarse, porque
cada una condiciona la validez de la siguiente. No tendría sentido, por
ejemplo, entrenar modelos más complejos antes de ampliar los datos, ni medir
ahorros antes de disponer de registros de riego. Este orden es coherente con la
conclusión del apartado 4.3: la principal limitación del proyecto es la
cobertura de los datos, no la falta de algoritmos.

## 6.3.1. Ampliación de la evidencia

La primera mejora consiste en ampliar el conjunto con varias campañas, otras
estaciones de Almería y, después, otros cultivos. La extracción meteorológica
ya admite estación y periodo, pero las necesidades del cultivo se incorporan
mediante un CSV descargado de la web de SiAR y sus metadatos. La ETL ya permite
seleccionar explícitamente ese CSV y el raw meteorológico, y comprueba que
coincidan estación y campaña. Antes de ampliar el piloto falta un catálogo de
casos seleccionable en la interfaz y comprobar la aplicabilidad agronómica de
cada calendario. Las cuotas de la API afectan a la
descarga climática, mientras que los CSV de necesidades requieren una gestión
separada y una nueva revisión de calidad. Con varias campañas
podrá validarse por bloques completos, reservando campañas y estaciones enteras
para medir la generalización temporal y espacial sin estimaciones optimistas
del error (Roberts et al., 2017). Esta ampliación permitirá comprobar si la
ventaja de la vía ET0 × Kc se mantiene en cultivos con un coeficiente de
variación gradual y repetir con más datos la comparación de los seis enfoques
del capítulo 4.

## 6.3.2. Mejora del motor de recomendación

La prioridad principal para la siguiente iteración es incorporar un balance
hídrico real de la parcela. Requiere combinar sensores IoT de humedad del suelo,
capacidad de retención, profundidad radicular, precipitación efectiva y registro
del riego realmente aplicado. Con estas entradas el sistema podría estimar el
agotamiento admisible propuesto en FAO-56, decidir no solo cuánto sino cuándo
regar y aprovechar la lluvia realmente almacenada en el suelo (Allen et al.,
1998). Los sensores facilitan una telemetría continua, pero no sustituyen la
caracterización agronómica ni el registro de las actuaciones: recomendar una
dosis no prueba que se haya ejecutado. Cualquier mejora de precisión deberá
comprobarse mediante observaciones y ensayos de campo. Con esa información, la
reducción proporcional por dotación podría sustituirse por una estrategia de
riego deficitario que concentre el déficit en las fases menos sensibles del
cultivo (Fereres & Soriano, 2007).

La segunda prioridad es anticipar cambios de tiempo mediante una ET0 prevista,
especialmente en los días 4 a 7 del horizonte. El motor ya admite esta entrada,
de modo que el trabajo pendiente es de datos y de evaluación.
La predicción municipal de AEMET OpenData describe los días
posteriores a cada emisión y el proyecto no dispone de emisiones pasadas, por
lo que el histórico debe construirse archivando de forma programada cada
predicción. Con ese histórico podrán compararse dos alternativas: estimar la
ET0 con la ecuación de Hargreaves calibrada frente a la ET0 de Penman-Monteith
observada en la estación (Allen et al., 1998), o estudiar el pronóstico de
necesidades netas que publica SiAR, calculado con previsiones de ET0 y lluvia
de AEMET. Este último cubre seis días (Sistema de Información Agroclimática
para el Regadío, s. f.), por lo que no resuelve por sí solo el séptimo día del
horizonte del DSS. Además, si se usa como entrada, su
comparación con la referencia SiAR debe declararse como contraste entre
productos relacionados, no como validación independiente. Cualquiera de estas
vías debe evaluarse con la misma disciplina temporal que el resto del trabajo,
utilizando solo predicciones emitidas antes de cada fecha objetivo, y sustituir
a la vía actual únicamente si mejora el error por horizonte de la Tabla 5.5.
El mismo archivo permitirá evaluar si conviene descontar la lluvia prevista
en lugar de limitarse a avisar.

La tercera prioridad es reevaluar el aprendizaje automático una vez ampliados
los datos. Debería reintroducirse
con un papel distinto al del capítulo 4: no para predecir directamente la
necesidad, sino para aprender la corrección de la estimación física, es decir,
el residuo entre la vía ET0 × Kc y la referencia, a partir de las variables
meteorológicas y de predicción disponibles en el momento de emitir. Este
planteamiento conserva la explicabilidad de la base agronómica y reduce el
riesgo de sobreajuste. En paralelo, los niveles de confianza actuales,
definidos mediante reglas a partir del error medio por horizonte, deberían
sustituirse por intervalos de predicción, de forma que cada dosis se acompañe
de un rango cuantificado (Hyndman & Athanasopoulos, 2021).

## 6.3.3. Validación en condiciones de uso

Antes de cualquier despliegue es necesario evaluar el prototipo con técnicos de
cooperativas y agricultores, mediante tareas concretas de interpretación y
decisión y con medidas de comprensión, utilidad percibida y confianza (Rose et
al., 2016). Esta evaluación puede realizarse con la aplicación actual y
respondería a una pregunta que el trabajo no ha podido contestar: si las
explicaciones y los avisos resultan útiles a quienes deben decidir.

La única forma de cuantificar el ahorro de agua o el efecto sobre la producción
es un ensayo en campo que registre el riego aplicado, la humedad del suelo y el
rendimiento en parcelas que sigan la recomendación y en parcelas de control. El
sistema ya exporta cada recomendación con sus parámetros y su origen, de manera
que el archivo de recomendaciones emitidas puede compararse directamente con el
riego real. Solo entonces podrá sustituirse la referencia calculada por una
referencia medida y evaluarse el sistema frente al problema que motivó el
trabajo.

## 6.3.4. Evolución de la plataforma

La industrialización del prototipo debería abordarse cuando las mejoras
anteriores justifiquen un uso continuado. Comprende persistir catálogos,
recomendaciones y metadatos en la base de datos relacional prevista en el
apartado 3.2.2, programar la ingesta diaria con un orquestador, que puede ser
Apache Hop u otra herramienta equivalente, empaquetar el sistema con Docker y
permitir que la aplicación seleccione estación y cultivo entre los casos
declarados. Los indicadores del Boletín Hidrológico del MITECO pueden
incorporarse como contexto a escala de cuenca, para advertir de situaciones de
escasez, sin pretender deducir de ellos la dotación de una parcela. El
procesamiento distribuido con PySpark solo estaría justificado si el sistema se
extendiera a escala nacional; con el volumen actual añadiría complejidad sin un
beneficio demostrable, como se señaló en el apartado 3.2.4.

## 6.3.5. Consideración final

El trabajo se planteó como la construcción de una cadena completa de datos y
decisión, con el aprendizaje automático como uno de sus componentes. El piloto
obliga a reconsiderar el papel de ese componente. Con los datos disponibles, la
mejora no ha procedido del algoritmo, sino de estructurar correctamente el
problema: separar lo incierto de lo conocido, impedir que la información futura
contamine la evaluación y hacer visible la incertidumbre en lugar de
esconderla. El aprendizaje automático conserva su lugar en el sistema, pero
como herramienta para corregir una base física cuando existan datos
suficientes, no como sustituto de ella. La frontera de mejora del proyecto no
está, por tanto, en el modelo, sino en los datos: más campañas, predicciones
archivadas y, sobre todo, información medida en las parcelas en las que se toma
la decisión.
