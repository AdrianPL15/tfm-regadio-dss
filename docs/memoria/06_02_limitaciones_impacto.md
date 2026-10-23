# 6.2. Limitaciones e impacto del proyecto

## 6.2.1. Limitaciones y alcance de las conclusiones

Las limitaciones del piloto se han señalado a lo largo de los capítulos
anteriores. Reunidas, permiten delimitar qué conclusiones son válidas y cuáles
no pueden extraerse todavía. Se agrupan a continuación en cinco tipos, según la
validez que comprometen, y la Tabla 6.2 relaciona cada una con la afirmación
que impide y con la línea de mejora que la aborda.

La limitación más importante es de validez de constructo. La variable objetivo
y la referencia de toda la evaluación es la necesidad neta calculada por SiAR,
que aplica la metodología FAO-56 a las condiciones de una estación y a un
calendario de cultivo estándar (Allen et al., 1998). Un error pequeño frente a
ella demuestra que el sistema reproduce y anticipa bien un cálculo oficial, no
que la dosis sea la adecuada para una parcela concreta, cuyo suelo, cubierta,
marco de plantación y estado del cultivo pueden diferir de los supuestos de la
estación.

La segunda es de validez externa. Todo se ha evaluado con una estación, un
cultivo y una campaña. El calendario del pimiento, con saltos bruscos del Kc
entre fases, favorece precisamente al método propuesto, cuya ventaja sería
menor en un cultivo con un coeficiente que varíe de forma gradual. El tramo de
prueba, septiembre, es además atípico: sus necesidades rondan 1 mm diario, por
lo que sus errores absolutos son poco representativos del verano.

La tercera afecta a la capacidad predictiva. El sistema no dispone de una ET0
prevista contrastada. AEMET está integrado y normalizado, pero sus predicciones
no coinciden temporalmente con la campaña de 2025, y sin un histórico de
emisiones no es posible calibrar ni evaluar una ET0 futura sin incurrir en fuga
de información. En consecuencia, cualquier horizonte futuro depende de que el
tiempo no cambie demasiado respecto al periodo reciente; el cuarto día se
utiliza solo como umbral prudencial de aviso en la interfaz. En la prueba el sistema
llega a perder frente a la persistencia en el séptimo día. Tampoco descuenta la
lluvia prevista. Es una decisión prudente en un clima con 2,51 mm de
precipitación efectiva en toda la campaña, pero en zonas más lluviosas
trasladaría al usuario un número mayor de avisos que resolver.

La cuarta es funcional. El sistema decide cuánto regar, pero no cuándo, porque
sin balance hídrico del suelo trata todas las necesidades como diarias. La
restricción de agua se aplica mediante una reducción proporcional, que no
reparte el déficit según la sensibilidad de cada fase del cultivo (Fereres &
Soriano, 2007). La aplicación, por su parte, trabaja con un caso fijo, no
conserva un histórico de consultas y no se ha probado con agricultores ni
técnicos.

La quinta es de arquitectura y supone una desviación respecto al anteproyecto.
MySQL, Apache Hop, Docker y PySpark no se han implementado, y el cuadro de
mando en Power BI o Tableau se ha sustituido por una aplicación en Streamlit.
Las razones se exponen en los apartados 3.2.2 y 5.2.1 y son defendibles para el
volumen del piloto, pero deben declararse como lo que son: el prototipo
demuestra el flujo de datos y de decisión, no una plataforma desplegable.

**Tabla 6.2. Limitaciones del piloto, alcance de las conclusiones y línea de mejora asociada.**

| Limitación | Qué no puede afirmarse todavía | Línea de mejora |
|---|---|---|
| Referencia calculada por SiAR, sin riego aplicado ni respuesta del cultivo | Que las dosis sean óptimas para una parcela ni que reduzcan el consumo de agua | Validación en campo (6.3.3) |
| Una estación, un cultivo y una campaña | Que los resultados se generalicen a otras zonas, cultivos o años | Ampliación de la evidencia (6.3.1) |
| Sin ET0 prevista ni histórico de predicciones | Que el sistema anticipe cambios de tiempo en los horizontes largos | ET0 prevista (6.3.2) |
| Sin balance hídrico del suelo | Que el sistema determine el momento adecuado del riego | Balance hídrico y riego deficitario (6.3.2) |
| Restricción hídrica introducida como dotación del usuario | Que la recomendación refleje la disponibilidad oficial de agua | Indicadores hidrológicos (6.3.4) |
| Interfaz sin evaluación con usuarios | Que las recomendaciones se comprendan y se adopten | Evaluación con usuarios (6.3.3) |
| Arquitectura objetivo no implementada | Que el prototipo pueda operar de forma continua | Evolución de la plataforma (6.3.4) |

## 6.2.2. Impacto del proyecto

El impacto debe valorarse con la misma prudencia. El trabajo no ha demostrado
ahorro de agua, y no podía hacerlo con el diseño adoptado. Conviene recordar,
además, que una dosis menor en parcela no equivale necesariamente a un ahorro
neto a escala de cuenca, porque parte de las pérdidas retorna al sistema
hidrológico (Perry, 2007). Con esa salvedad, el proyecto presenta tres
resultados observables en el prototipo y un impacto potencial. Ninguno de los
tres primeros equivale a un beneficio cuantificado en una explotación real.

El primero es una capacidad funcional comprobada. El sistema transforma datos públicos y gratuitos en
una dosis diaria y semanal expresada en milímetros y en metros cúbicos por
parcela, acompañada de su explicación y sin necesidad de sensores. Su valor
práctico se concentra en los cambios de fase. En la semana analizada en el
apartado 5.2.3, la persistencia habría planificado 6,77 mm menos de los que
necesitó el cultivo, un 18 % de la referencia, justo al entrar en una fase de
mayor demanda; el sistema se desvió un 4,9 %. Es el tipo de error que un
calendario fijo o la repetición de la última dosis no ponen de manifiesto y que
podría traducirse en un déficit hídrico si se utilizara para decidir sin otros
controles; el ejemplo retrospectivo no demuestra que ocurriera en una parcela.

El segundo es un hallazgo que reordena las prioridades de mejora. El análisis
de sensibilidad mostró que un error de diez puntos en la eficiencia de la
instalación produce una desviación de alrededor del 12 % en la dosis bruta, muy
superior al error de estimación de la necesidad neta medido en este trabajo.
Para una explotación, caracterizar la eficiencia y la uniformidad de su
instalación aportaría más precisión que refinar el modelo de ET0 (Burt et al.,
1997). La observación es pertinente también para las políticas de
digitalización del regadío (Real Decreto 854/2022, 2022): una herramienta
digital solo convierte su precisión en ahorro si conoce la instalación sobre la
que se aplica.

El tercero es metodológico. El repositorio constituye una plantilla
reutilizable para otros cultivos y estaciones, porque la configuración del
caso, la ETL y el motor están desacoplados. Además, documenta con evidencias
reproducibles una advertencia que la literatura formula en términos generales:
la elección del algoritmo depende del tamaño y la estructura de los datos, y
los modelos complejos deben contrastarse con líneas base sencillas antes de
adoptarse (Benos et al., 2021; Liakos et al., 2018).

El impacto potencial depende de la adopción. La trayectoria de los sistemas de
apoyo a la decisión agrícola muestra que muchas herramientas técnicamente
correctas no llegan a utilizarse (McCown, 2002), y que la confianza, la
facilidad de uso y la relevancia percibida condicionan su adopción (Rose et
al., 2016). El prototipo responde a esas condiciones con explicaciones en
lenguaje llano, avisos visibles y un formato numérico adaptado al usuario
español, pero mientras no se evalúe con usuarios reales su efecto sobre la toma
de decisiones sigue siendo una hipótesis.
