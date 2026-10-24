"""Update the review copy of the TFM to match the deployed October 2026 DSS.

The input remains unchanged. Index page numbers are refreshed separately after
rendering because the document uses static index entries.
"""

from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/memoria/TFM_revision_integracion_ETC_AEMET_2026-10-24.docx"
OUTPUT = ROOT / "docs/memoria/TFM_revision_final_contenido_2026-10-24.docx"


REPLACEMENTS = {
    18: (
        "Este Trabajo Fin de Máster presenta un sistema de apoyo a la decisión que propone "
        "dosis orientativas de riego diarias y semanales. El piloto inicial evaluó pimiento "
        "en la estación AL01 La Mojonera (Almería) durante 2025: con 148 referencias válidas, "
        "una vía física basada en ET0 reciente y Kc redujo el MAE a un día frente a la "
        "persistencia un 7 % en desarrollo y un 25 % en la prueba reutilizada. La ampliación "
        "incorpora seis combinaciones de cultivo y estación con datos SiAR hasta octubre de "
        "2026 y compara modelos independientes de ETc con esa vía física. En los tres cultivos "
        "activos fue más precisa la vía física en su tramo de prueba. La aplicación pública "
        "consulta SiAR y la previsión de lluvia de AEMET; estima primero la demanda antes de "
        "lluvia, descuenta después la fracción de precipitación considerada aprovechable y "
        "muestra la dosis y su procedencia. La evaluación retrospectiva del motor corresponde "
        "al piloto de 2025: no incluye previsiones AEMET archivadas ni riego realmente aplicado. "
        "Por ello, el trabajo demuestra funcionamiento y trazabilidad, pero no ahorro de agua "
        "ni adecuación de la dosis a una parcela sin validación en campo."
    ),
    258: (
        "Los datos permiten comprobar el recorrido técnico, pero no una optimización "
        "agronómica generalizable. La evaluación retrospectiva del DSS usa una estación, un "
        "cultivo y una campaña; la ampliación predictiva reúne seis combinaciones de tres "
        "estaciones y hasta dos campañas. En todos los casos la referencia de SiAR es "
        "calculada y faltan riego real, humedad del suelo, eficiencia medida de la instalación "
        "y respuesta productiva. Estas limitaciones condicionan la interpretación de los "
        "capítulos 4 y 5."
    ),
    281: (
        "Los módulos generan salidas reproducibles a partir de datos y parámetros conocidos. "
        "La suite de 97 pruebas comprueba extracción, protección de credenciales, escritura "
        "raw, normalización, calidad, variables, selección temporal, modelos de ETc y "
        "reglas del motor. Incluye controles para impedir el uso de información posterior "
        "a la emisión. Las figuras y resúmenes se regeneran desde los archivos del proyecto."
    ),
    264: (
        "1. Configuración. La ubicación, el cultivo y el periodo son parámetros de ejecución. "
        "En la aplicación, el usuario escoge entre combinaciones de comunidad, provincia, "
        "cultivo, estación y campaña con CSV verificados; además indica fecha, horizonte y "
        "datos de la parcela. El catálogo actual no abarca todas las zonas de España."
    ),
    450: (
        "El conjunto original de pimiento AL01 en 2025 permite verificar el flujo técnico, "
        "establecer una línea base y detectar problemas de integración. Sus 148 etiquetas "
        "válidas no bastan para afirmar generalización. La ampliación posterior del apartado "
        "4.3.10 añade seis combinaciones, pero sus pruebas tampoco acreditan transferencia "
        "a otras parcelas ni ahorro de agua."
    ),
    510: (
        "El reentrenamiento amplía la evidencia, pero la etiqueta sigue siendo una necesidad "
        "calculada por SiAR, no riego aplicado. La persistencia predice a un día con el dato "
        "anterior conocido. Sin previsiones AEMET archivadas antes de cada fecha objetivo no "
        "se puede medir su aportación. Estos seis modelos de necesidad neta se conservan como "
        "experimento; la aplicación compara otros seis modelos de ETc, descritos a continuación."
    ),
    551: (
        "El motor puede consultarse desde la línea de comandos o mediante la aplicación "
        "Streamlit. Ambas vías utilizan las reglas de src/dss/engine.py, pero la interfaz pública "
        "añade la actualización de SiAR, la consulta de lluvia AEMET y la comparación con "
        "modelos de ETc. La validación retrospectiva del apartado 5.3 corresponde a la vía "
        "agronómica del piloto de 2025; no evalúa prospectivamente estas incorporaciones."
    ),
    557: (
        "La pantalla destaca primero la dosis del día en L/m², el volumen de la parcela "
        "en m³ y el equivalente por hectárea. Después presenta el total orientativo del "
        "horizonte y un gráfico diario. Los avisos de vigencia, periodo de cultivo y cobertura "
        "de lluvia aparecen junto a la recomendación. La procedencia, el método utilizado, "
        "la comparación ETc entre modelo y cálculo físico, la previsión AEMET y la tabla "
        "detallada quedan en bloques desplegables. Un botón descarga el resultado en CSV."
    ),
    560: (
        "El ejemplo histórico analiza una planificación emitida el 28 de junio de 2025 "
        "con siete días de horizonte; cruza el cambio de Kc de 0,70 a 0,90 el 1 de julio. "
        "Supone goteo con eficiencia del 90 % y una parcela de 1,5 ha. La Figura 5.2 "
        "conserva una captura de la versión anterior de la interfaz con la referencia SiAR "
        "superpuesta. La interfaz pública actual se organiza como describe 5.2.2."
    ),
    562: (
        "Figura 5.2. Captura de la interfaz anterior para la planificación histórica "
        "emitida el 28 de junio de 2025, con referencia SiAR superpuesta."
    ),
    575: (
        "La aplicación es una demostración pública y no guarda un histórico de consultas por "
        "parcela ni dispone de cuentas de usuario. Lee CSV verificados y puede actualizar en "
        "memoria el caso vigente desde SiAR; el botón consulta también AEMET y descuenta "
        "lluvia solo cuando existe una cantidad horaria completa. No convierte esa previsión "
        "en ET0 futura contrastada ni dispone de un archivo de emisiones pasadas para "
        "evaluar el efecto de AEMET. Los días posteriores a mañana son orientativos y deben "
        "recalcularse. La interfaz tampoco se ha probado con agricultores o técnicos. La "
        "facilidad de uso y la relevancia percibida condicionan la adopción de estos sistemas "
        "(Rose et al., 2016), por lo que esa prueba con usuarios sigue pendiente."
    ),
    633: (
        "El primer comando genera el informe del DSS de 2025 y sus figuras; el segundo, "
        "la Figura 5.1, y el tercero ejecuta las pruebas. Los experimentos ampliados se "
        "regeneran con python -m src.models.retrain_cases_2026 y python -m "
        "src.models.train_etc_for_dss. La aplicación se abre desde el enlace público o "
        "mediante streamlit run src/dss/app_streamlit.py. El motor evaluado en este "
        "capítulo no equivale a una validación de la consulta AEMET actual."
    ),
    637: (
        "El objetivo general era diseñar, implementar y evaluar un DSS que convirtiera datos "
        "agroclimáticos y parámetros de parcela en recomendaciones operativas y trazables. "
        "Se ha alcanzado como prueba de concepto acotada: el repositorio permite repetir la "
        "ETL, los ensayos predictivos y la validación retrospectiva del motor de 2025 para "
        "pimiento AL01. La ampliación incluye seis combinaciones de cultivo y estación y una "
        "aplicación pública que consulta SiAR y lluvia prevista de AEMET para casos vigentes. "
        "No se dispone de previsiones históricas alineadas para evaluar retrospectivamente "
        "esa integración ni de riego aplicado o respuesta del cultivo para validar la dosis "
        "en parcela. La disponibilidad de agua se representa mediante una dotación que "
        "introduce el usuario, no mediante una asignación oficial parcelaria."
    ),
    646: (
        "La cuarta aportación es la reproducibilidad. El repositorio conserva los CSV SiAR "
        "acotados, los protocolos de modelado y las métricas por caso, el motor y la demo "
        "pública. Los modelos de necesidad neta del experimento quedan como artefactos "
        "locales reproducibles; los seis artefactos pequeños de ETc sí se versionan para "
        "su uso en Streamlit. Los módulos de entrenamiento y la suite de pruebas verifican "
        "calidad, orden temporal y ausencia de variables del día objetivo."
    ),
    652: (
        "La tercera limitación afecta a la predicción meteorológica. No existe una ET0 "
        "futura contrastada ni un archivo histórico de previsiones AEMET emitidas antes de "
        "cada fecha objetivo. Por ello, los resultados retrospectivos de 2025 no miden la "
        "integración actual. La aplicación sí descuenta una fracción supuesta de la lluvia "
        "prevista cuando AEMET proporciona una cantidad horaria completa; no está calibrada "
        "frente a lluvia efectiva ni almacenamiento del suelo. Para los días posteriores a "
        "mañana se mantiene una estimación provisional de ET0 y Kc. En la prueba original, "
        "el séptimo día perdió frente a la persistencia."
    ),
    654: (
        "La quinta limitación es de arquitectura. MySQL, Apache Hop, Docker y PySpark no "
        "se han implementado, y el cuadro de mando de Power BI o Tableau se sustituyó por "
        "Streamlit. La aplicación está publicada y puede consultarse, pero la persistencia "
        "de consultas, la operación continuada y el control de acceso no están resueltos. "
        "Las razones y el alcance de estas decisiones se exponen en 3.2.2 y 5.2.1."
    ),
    666: (
        "La primera mejora consiste en ampliar campañas, estaciones y cultivos. El prototipo "
        "ya ofrece seis combinaciones en tres estaciones, pero solo entre casos descargados "
        "y verificados. La extracción meteorológica admite estación y periodo; las "
        "necesidades se aportan con CSV SiAR y metadatos. Falta automatizar un catálogo "
        "amplio y contrastar la aplicabilidad agronómica de cada calendario. Con campañas "
        "adicionales podrán reservarse bloques completos para medir transferencia temporal "
        "y espacial (Roberts et al., 2017)."
    ),
    668: (
        "Para anticipar cambios de tiempo es prioritario obtener una ET0 futura validada, "
        "especialmente para los días 4 a 7. El motor admite esa entrada, pero la aplicación "
        "usa de momento ET0 observada reciente. AEMET aporta lluvia prevista al cálculo "
        "actual; no hay emisiones históricas archivadas que permitan evaluar su aportación "
        "frente a la lluvia finalmente efectiva. Ese archivo deberá registrar emisión, "
        "periodo de validez y observación posterior. Con él se podría evaluar una ET0 "
        "derivada de variables pronosticadas o el producto de necesidades previstas de SiAR "
        "(Sistema de Información Agroclimática para el Regadío, s. f.), sin confundir "
        "productos relacionados con una validación independiente. La sustitución de la "
        "vía actual exigiría mejorar el error por horizonte en bloques temporales nuevos."
    ),
    669: (
        "Los seis modelos de ETc actuales se utilizan como contraste de la vía física y "
        "solo pueden determinar la dosis cuando mejoran su MAE de prueba y existe una "
        "observación del día anterior. Con más campañas y previsiones archivadas convendrá "
        "ensayar una corrección de la estimación física mediante el residuo entre ET0 × Kc "
        "y la referencia, usando únicamente información disponible al emitir. La mejora "
        "deberá evaluarse en bloques temporales nuevos, sin reutilizar para selección la "
        "misma prueba final. Los niveles de confianza actuales, definidos por reglas, "
        "podrían reemplazarse por intervalos calibrados (Hyndman & Athanasopoulos, 2021)."
    ),
    672: (
        "Antes de un uso agronómico continuado se debe evaluar la aplicación con técnicos "
        "y agricultores mediante tareas de interpretación y decisión, midiendo comprensión, "
        "utilidad percibida y confianza (Rose et al., 2016). La demo pública permite hacer "
        "esa evaluación, pero la publicación del enlace no constituye validación con usuarios."
    ),
    675: (
        "La industrialización exigiría persistir catálogos, recomendaciones y metadatos en "
        "una base de datos, programar la ingesta y gestionar acceso y operación. Apache Hop "
        "y Docker son opciones previstas, todavía no implementadas. La aplicación ya deja "
        "elegir entre los casos SiAR declarados; una expansión nacional requeriría un "
        "catálogo dinámico, controles agronómicos por cultivo y cobertura de estaciones. "
        "Los indicadores del MITECO podrían aportar contexto de cuenca, sin deducir de "
        "ellos la dotación de una parcela. PySpark solo estaría justificado con un volumen "
        "muy superior al del piloto, como se indicó en 3.2.4."
    ),
    677: (
        "El trabajo muestra el valor de separar la demanda del cultivo, la lluvia prevista "
        "y las reglas de aplicación de la dosis. En la evaluación original del pimiento, "
        "la vía física anticipó mejor la referencia SiAR que la persistencia en los tramos "
        "estudiados. En la ampliación, cinco de los seis casos de ETc conservaron la vía "
        "física tras comparar errores de prueba; el único modelo favorecido corresponde a "
        "algodón, fuera de ciclo en octubre. La integración de AEMET es funcional, pero "
        "faltan previsiones archivadas y mediciones de parcela para conocer su efecto real. "
        "La siguiente mejora depende sobre todo de datos y validación externa, no de "
        "aumentar sin más la complejidad del algoritmo."
    ),
    712: (
        "El código, los CSV de muestra y las salidas se encuentran en el repositorio del "
        "equipo https://github.com/al1sr/tfm-regadio-dss. La versión desplegada se aloja "
        "en el fork https://github.com/AdrianPL15/tfm-regadio-dss; las rutas siguientes "
        "corresponden a este último en el commit de entrega. Los ensayos con CSV "
        "versionados y las pruebas no requieren credenciales. La demo pública está en "
        "https://tfm-regadio-dss-adrianpl15.streamlit.app/. Las consultas nuevas a "
        "AEMET requieren una clave privada fuera de Git."
    ),
    716: (
        "Desde la raíz del fork, tras crear un entorno virtual e instalar requirements.txt, "
        "los siguientes comandos regeneran el análisis original sin consultar las APIs. "
        "El reentrenamiento adicional se reproduce con los dos comandos que siguen:"
    ),
}


def replace_text_preserving_paragraph(paragraph, value):
    if not paragraph.runs:
        paragraph.add_run(value)
        return
    paragraph.runs[0].text = value
    for run in paragraph.runs[1:]:
        run.text = ""


def main():
    doc = Document(SOURCE)
    for index, value in REPLACEMENTS.items():
        replace_text_preserving_paragraph(doc.paragraphs[index], value)

    for run in doc.paragraphs[554].runs:
        run.text = run.text.replace("(Streamlit, 2024)", "(Streamlit, 2026)")
    for run in doc.paragraphs[705].runs:
        run.text = run.text.replace("(2024)", "(2026)").replace("1.39.0", "1.66.0")
    replace_text_preserving_paragraph(
        doc.paragraphs[164],
        "Figura 5.2. Captura de la interfaz anterior para la planificación histórica "
        "emitida el 28 de junio de 2025, con referencia SiAR superpuesta.\t63",
    )

    objectives = doc.tables[27]
    objectives.cell(3, 3).text = (
        "El piloto de 2025 caracteriza una localización; el análisis posterior añade seis "
        "combinaciones. Faltan datos de parcela y disponibilidad de agua."
    )
    objectives.cell(6, 3).text = (
        "Demo pública con selección entre casos SiAR verificados y consulta AEMET para "
        "casos vigentes. Sin evaluación con usuarios ni catálogo nacional."
    )
    objectives.cell(7, 2).text = "Parcial"
    objectives.cell(7, 1).text = (
        "Apartado 5.3; validación retrospectiva, 13 escenarios y 97 pruebas automáticas"
    )
    objectives.cell(7, 3).text = (
        "Motor original evaluado frente a SiAR con trece escenarios; ampliación de ETc y "
        "AEMET funcional, sin prueba histórica alineada ni validación en campo."
    )

    limitations = doc.tables[28]
    limitations.cell(2, 0).text = "DSS evaluado en pimiento 2025; modelos ampliados a seis combinaciones"
    limitations.cell(3, 0).text = "Sin ET0 futura validada ni previsiones AEMET archivadas"
    limitations.cell(3, 1).text = "Que el descuento de lluvia o los horizontes largos mejoren la dosis real"
    limitations.cell(7, 1).text = "Que la demo publicada equivalga a una plataforma operativa continua"

    evidence = doc.tables[29]
    evidence.cell(3, 1).text = (
        "src/models/train_evaluate.py y retrain_cases_2026.py; "
        "docs/data_samples/model_evaluation_4_3.json y model_retraining_2026.json"
    )
    evidence.cell(4, 1).text = (
        "src/models/train_etc_for_dss.py; src/dss/predict_etc.py, engine.py y "
        "app_streamlit.py; docs/data_samples/etc_model_deployment_2026.json y "
        "dss_validation_5_3.json; modelos en models/deployed_etc_2026/"
    )

    # Preserve table style when adding a short reproducibility subsection.
    p = doc.paragraphs[721]
    p.insert_paragraph_before("python -m src.models.retrain_cases_2026", style="Normal")
    p.insert_paragraph_before("python -m src.models.train_etc_for_dss", style="Normal")

    # The final note repeats the scope already explained in the annex introduction
    # and chapters 4–5; removing it keeps the annex on one page.
    final_note = doc.paragraphs[-1]
    final_note._element.getparent().remove(final_note._element)

    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
