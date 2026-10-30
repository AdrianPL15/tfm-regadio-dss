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
hídrico real de la parcela. La instrumentación podría combinar sondas
capacitivas FDR o TDR para contenido volumétrico y tensiómetros para potencial
matricial, instalados a varias profundidades representativas de la zona
radicular. Como configuración inicial se propone un registro frecuente y una
agregación horaria; Sui (2017) documenta un caso con lectura cada minuto,
promedio horario y sensores a tres profundidades. La frecuencia definitiva
deberá ajustarse al suelo, cultivo y sistema de riego. La tubería de datos
controlaría rango físico, valores ausentes, deriva, conectividad y calibración
específica del suelo antes de alimentar el DSS. Junto con capacidad de
retención, profundidad radicular, precipitación efectiva y riego realmente
aplicado, estas entradas permitirían estimar el agotamiento admisible de FAO-56,
decidir no solo cuánto sino cuándo regar y aprovechar la lluvia almacenada
(Allen et al., 1998). La telemetría no sustituye la caracterización agronómica
ni prueba que una dosis recomendada se haya ejecutado. Cualquier mejora deberá
validarse en campo; después podría estudiarse un riego deficitario que concentre
el déficit en fases menos sensibles (Fereres & Soriano, 2007).

Como complemento espacial, podría evaluarse la teledetección de Copernicus
Sentinel-2 para estimar índices de vegetación como NDVI y observar diferencias
de vigor dentro de la parcela (Drusch et al., 2012). Estos índices no
sustituirían automáticamente el Kc de calendario. Servirían para investigar un
Kc dinámico por cultivo y parcela, calibrado frente a sensores, observaciones de
campo y ETc de referencia. La nubosidad, la frecuencia de adquisición y la
resolución disponible deberían tratarse como fuentes de ausencia e
incertidumbre, de modo que el sistema mantuviera la vía agronómica cuando la
imagen no fuese representativa.

La segunda prioridad ya no es construir una primera ET0 prevista, sino validar
prospectivamente la predicción Ridge `h=1…9`, ampliar la cobertura de Z06 y
vigilar su deriva. Una tarea diaria debe archivar cada emisión y contrastarla
después con el primer valor SiAR disponible y con su posible revisión. El
umbral de despliegue exige al menos 30 fechas objetivo distintas, consolidadas y pareadas por estación y horizonte. Sobre una
ventana móvil máxima de 60 fechas por grupo, Ridge debe reducir al menos un 5 % el MAE del
respaldo de media de siete días; si deja de cumplirse, el sistema vuelve a ese
respaldo. El reentrenamiento se programa una vez al año, al cerrar y auditar la
campaña, y solo sustituye al artefacto vigente si supera el mismo control
temporal y prospectivo.

Como evolución adicional,
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
utilizando solo predicciones emitidas antes de cada fecha objetivo, y añadirse
a la vía actual únicamente si mejora el error por horizonte.
El mismo archivo permitirá evaluar si conviene descontar la lluvia prevista
en lugar de limitarse a avisar.
También permitiría modelizar el error local de AEMET mediante dos tareas
separadas: clasificación de la ocurrencia de lluvia y regresión de la cantidad
observada frente a la prevista. Este posprocesado corregiría sesgos locales y
cuantificaría la incertidumbre; no sustituiría la predicción oficial. El
entrenamiento respetaría la hora de emisión y reservaría bloques temporales
posteriores para prueba.

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

La evaluación de uso debería reproducir además las condiciones del campo. Una
versión orientada al regante tendría que adoptar un diseño mobile-first, alto
contraste para lectura bajo luz solar, objetivos táctiles amplios y lenguaje
directo. También debería tolerar conectividad intermitente mediante una vista
local de la última recomendación válida, mostrando siempre su fecha y vigencia
para evitar que una dosis almacenada se interprete como actual. Estas decisiones
se validarían con pruebas de tarea y accesibilidad, no solo mediante una
revisión estética de la interfaz.

La única forma de cuantificar el ahorro de agua o el efecto sobre la producción
es un ensayo en campo que registre el riego aplicado, la humedad del suelo y el
rendimiento en parcelas que sigan la recomendación y en parcelas de control. El
sistema ya exporta cada recomendación con sus parámetros y su origen, de manera
que el archivo de recomendaciones emitidas puede compararse directamente con el
riego real. Solo entonces podrá sustituirse la referencia calculada por una
referencia medida y evaluarse el sistema frente al problema que motivó el
trabajo.

## 6.3.4. Evolución de la plataforma

La industrialización debería ser gradual y proporcional al volumen real. Una
primera etapa programaría procesos ligeros en Python o funciones gestionadas
que conservaran cada respuesta JSON, su hora de emisión y su procedencia en una
capa raw inmutable de almacenamiento de objetos. Una segunda capa normalizaría
y particionaría los datos en Parquet por fuente, estación y fecha, con catálogo,
controles de calidad y trazabilidad. Una base relacional quedaría reservada
para usuarios, parcelas y recomendaciones; el histórico analítico se consultaría
con DuckDB o Polars mientras el volumen sea moderado. Si una ampliación nacional
y multianual exigiera consultas concurrentes, podría incorporarse un motor SQL
distribuido como Trino, capaz de consultar formatos de tabla y archivos Parquet
sobre almacenamiento de objetos (Trino, s. f.). Esta evolución sigue los
principios de un lakehouse sin presentar Apache Hop, Impala, Hue o PySpark como
requisitos. El procesamiento distribuido solo se justificaría mediante
mediciones de volumen, latencia y coste que demostrasen una limitación del
enfoque ligero. La aplicación seguiría necesitando un catálogo agronómico
dinámico, operación, control de acceso y persistencia de consultas.

La decisión de escalar debería incluir una práctica FinOps proporcional al
producto: registrar coste por estación, cultivo y emisión, junto con consumo de
API, almacenamiento, cómputo, transferencia y mantenimiento. Para el volumen
actual, las ejecuciones bajo demanda y los archivos Parquet permiten mantener
una infraestructura ligera; esta viabilidad debe demostrarse con mediciones,
no presentarse como coste nulo. Antes de incorporar un motor distribuido se
compararían coste total, latencia y carga operativa con la solución vigente y
se fijarían umbrales que justificasen el cambio.

## 6.3.5. Operación, MLOps y control de deriva

La evolución del prototipo exige vigilar la cadena completa, no solo el error
del modelo. Cada ejecución debería registrar la versión del código, las fuentes,
la hora de emisión, la vigencia del último dato y la recomendación. Los cambios
de columnas, tipos, unidades o claves bloquearían la transformación; los datos
ausentes, duplicados o fuera de rango quedarían como incidencias visibles. Esta
disciplina evita que dependencias externas y cambios silenciosos acumulen deuda
técnica en el sistema (Sculley et al., 2015).

La monitorización estadística se separaría por cultivo y estación. Incluiría la
distribución de las variables, el MAE y el sesgo frente a SiAR, el error de
lluvia AEMET por horizonte, la latencia y el porcentaje de abstenciones. Una
alerta persistente abriría una evaluación, pero no desplegaría automáticamente
un modelo nuevo. El candidato tendría que compararse con el modelo vigente, la
persistencia y la vía física en un bloque temporal posterior, mantener los
controles de seguridad y conservar una versión reversible. Mientras no exista
una referencia de campo, esta vigilancia seguirá limitada a la referencia SiAR
y no permitirá detectar por sí sola una pérdida agronómica real.

## 6.3.6. Ciencia abierta y principios FAIR

La reutilización académica requiere que cada versión pueda encontrarse,
comprenderse y reproducirse. El repositorio incorpora un archivo de citación,
licencia para los activos propios, ficha del conjunto, diccionarios de variables,
procedencia y comandos de reproducción. Los formatos CSV y JSON, las fechas ISO
8601 y las claves de estación, cultivo y fecha facilitan la interoperabilidad.
Estas medidas aplican los principios FAIR sin confundir accesibilidad con
apertura irrestricta (Wilkinson et al., 2016).

Una versión posterior podría depositarse en Zenodo para obtener un DOI, pero
solo después de etiquetar una revisión inmutable y comprobar las condiciones de
redistribución de SiAR y AEMET. La licencia del código no relicencia los datos
de terceros. El depósito debería incluir la memoria, el código, los requisitos,
las pruebas, la ficha del conjunto y los metadatos, sin tokens ni respuestas raw
cuya redistribución no esté autorizada.

## 6.3.7. Consideración final

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
