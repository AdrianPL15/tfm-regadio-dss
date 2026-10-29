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

Existe además una dependencia estructural entre el estimador y la referencia:
SiAR calcula la necesidad a partir de ET0, Kc y precipitación efectiva, mientras
que la vía física del DSS combina ET0 reciente y el mismo calendario de Kc.
La comparación no es circular en sentido estricto, porque la ET0 del día
objetivo no entra en la estimación, pero ambos métodos comparten formulación
agronómica. Por ello, una buena concordancia mide fidelidad a la referencia
oficial y no constituye una validación independiente de la dosis agronómica.

La segunda es de validez externa. La evaluación detallada se concentra en
pimiento AL01 durante 2025, aunque se ha añadido una comprobación temporal con
coliflor AL01, alfalfa Z06 y alcachofa BA08 en 2026. El DSS supera a la
persistencia en los tres tramos finales reservados, pero cada cultivo adicional
aporta una sola campaña y no existe una prueba dejando fuera un año completo.
Por tanto, la ampliación comprueba el comportamiento cronológico en tres calendarios y regiones,
pero no demuestra generalización nacional ni estabilidad interanual.

La tercera afecta a la cobertura predictiva. El sistema dispone de ET0 Ridge
multianual por horizonte y descuenta la lluvia AEMET disponible, pero su
validación prospectiva acaba de comenzar y aún no contiene 30 casos
consolidados. Además, la cobertura retrospectiva de 2026 es cercana al 97 % en
AL01 y BA08, pero nula para Ridge en Z06 porque la fuente solo devolvió 13 días
continuos. Los intervalos mostrados son cuantiles empíricos de residuo, no una
garantía probabilística calibrada para una parcela concreta. Por ello, la
predicción a siete días es funcional, pero sigue sujeta a cobertura, deriva y
calidad de las fuentes.

La cuarta es funcional. El sistema propone una dosis diaria orientativa, pero
no determina cuándo regar, porque no mantiene un balance hídrico del suelo.
Tampoco conoce si una recomendación anterior llegó a aplicarse, por lo que no
la trata como riego realizado ni la descuenta de la necesidad posterior. La
restricción de agua se aplica mediante una reducción proporcional, que no
reparte el déficit según la sensibilidad de cada fase del cultivo (Fereres &
Soriano, 2007). La aplicación permite seleccionar nueve combinaciones
verificadas, pero no conserva un histórico de consultas y no se ha probado con
agricultores ni técnicos.

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
| Tres casos adicionales, pero una sola campaña por cultivo | Que los resultados se generalicen a todo el territorio o a otros años | Ampliación de la evidencia (6.3.1) |
| Dependencia estructural entre la referencia SiAR y la vía física | Que el bajo error equivalga a una validación agronómica independiente | Riego observado, sensores y validación de campo (6.3.2 y 6.3.3) |
| ET0 prevista sin evidencia prospectiva suficiente y cobertura nula de Ridge en Z06 | Que la mejora retrospectiva se mantenga operativamente en todas las estaciones | Monitorización diaria, consolidación y ampliación de cobertura (6.3.2) |
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
