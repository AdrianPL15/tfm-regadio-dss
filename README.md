# Sistema inteligente de apoyo a la decisión para la gestión hídrica agrícola

Trabajo Fin de Máster en Data Science. El proyecto desarrolla un sistema de apoyo a la decisión (DSS) orientado a estimar las necesidades de riego de distintos tipos de cultivo a partir de variables meteorológicas, agrometeorológicas e hidrológicas, con el fin de ofrecer recomendaciones de riego comprensibles y trazables para agricultores, cooperativas y gestores de explotaciones.

## Recorrido para revisar el TFM

| Orden | Qué abrir | Qué permite comprobar |
|---|---|---|
| 1 | [Aplicación pública](https://tfm-regadio-dss-adrianpl15.streamlit.app/) y [guía breve de la demo](docs/DEMO_TFM.md) | Selección de caso, consulta SiAR/AEMET, dosis, explicaciones y CSV descargable. |
| 2 | [Memoria candidata en PDF](docs/memoria/TFM_revision_final_2026-10-25.pdf) ([Word editable](docs/memoria/TFM_revision_final_2026-10-25.docx)) | Planteamiento, método, resultados y límites. |
| 3 | [Código de la interfaz](src/dss/app_streamlit.py), [motor de recomendación](src/dss/engine.py) y [actualización SiAR](src/data/refresh_siar_crop_needs.py) | Implementación que utiliza la demo. |
| 4 | [Volúmenes de la ETL](docs/data_samples/etl_volume_summary_4_1.csv), [evaluación de modelos](docs/data_samples/model_retraining_2026.json) y [validación del DSS](docs/data_samples/dss_validation_5_3.json) | Entradas, limpieza y resultados verificables sin ejecutar el proyecto. |

La app abre en **Recomendación (hoy o mañana)** y propone hoy por defecto cuando el cultivo está en ciclo y hay una observación SiAR reciente. **Revisión histórica (día cerrado)** utiliza datos observados para analizar días pasados; no mide el riego realmente aplicado. Los demás casos permiten consultar ejemplos históricos, identificados como tales. La [guía de la demo](docs/DEMO_TFM.md) indica qué enseñar y qué límites explicar al tutor.

## Alcance actual

La visión del producto permite que el usuario elija ubicación, cultivo y periodo para determinar las fuentes y los datos necesarios. El prototipo actual integra SiAR y AEMET mediante una ETL en Python con almacenamiento local por capas. La aplicación de demostración conserva tres combinaciones de 2025 y ofrece seis CSV oficiales de 2026: pimiento y coliflor en `AL01` La Mojonera (Almería), maíz y alfalfa en `Z06` Ejea de los Caballeros (Zaragoza), algodón y alcachofa en `BA08` Don Benito (Badajoz). **No** hay aún selección automática para cualquier estación/cultivo de España. En la comprobación del 25/10/2026, coliflor, alfalfa y alcachofa tenían Kc positivo y observaciones hasta el 23/10; permitían una estimación orientativa con Kc proyectado y previsión AEMET. La vigencia se verifica de nuevo en cada consulta y la interfaz avisa cuando no procede una predicción actual. Los otros cultivos permanecen como casos históricos. Se han reentrenado y evaluado seis modelos predictivos independientes por cultivo y estación con las campañas disponibles de 2025–2026; [el informe](docs/memoria/04_03_desarrollo_evaluacion_modelo_predictivo.md) distingue esos modelos del motor de reglas que usa Streamlit. No existe un modelo común ni se ha demostrado una mejora general de precisión. El encuadre del pimiento como cultivo al aire libre se mantiene como hipótesis del piloto, no acreditada por el CSV. La incorporación del Boletín Hidrológico del MITECO, la persistencia en MySQL y el cuadro de mando forman parte de la arquitectura objetivo. El sistema está pensado para apoyar, y no sustituir, el criterio agronómico del usuario final.

La app consulta además [modelos de ETc reentrenados](docs/INTEGRACION_ETC_AEMET_2026.md), distintos de los modelos de necesidad neta del experimento original. Compara su estimación previa a lluvia con `ET0 reciente × Kc`; utiliza para la dosis el método que tuvo menor MAE de prueba en cada caso y después aplica la lluvia cuantitativa AEMET, si está disponible. En los tres cultivos activos el método físico fue mejor en esa prueba, por lo que el modelo se muestra como contraste. Esta elección requiere validación prospectiva antes de afirmar que mejora la recomendación.

La demo pública se volvió a comprobar el 25/10/2026 sin iniciar sesión, incluida una consulta SiAR/AEMET, un escenario hipotético de lluvia y la descarga del CSV. Los [datos de 2026 y su alcance](docs/CAMPANAS_SIAR_2026.md) complementan los [casos retrospectivos de 2025](docs/DEMO_CASOS_SIAR_2025.md). La app separa la dosis del primer día del panorama provisional de hasta siete días y traduce los mm de riego a L/m², m³/ha y m³ para la parcela. El botón **Actualizar fuentes y generar recomendación** consulta el caso vigente en SiAR y la predicción municipal AEMET, validando la descarga antes de calcular; los CSV versionados siguen siendo instantáneas separadas que requieren su propia actualización.

## Autoría

Luis Moreno Díaz, Adrián Pérez Lombal, Manuel Ramos Alascio y Alicia Santamaría Román. Máster en Data Science, curso 2025 2026.

El uso de ChatGPT/Codex y Claude como herramientas de apoyo se declara en [`docs/USO_ASISTENTES_IA.md`](docs/USO_ASISTENTES_IA.md).

## Estructura del repositorio

```
├── data/                  Datos del proyecto (se excluyen raw y generados, salvo excepciones públicas aprobadas)
│   ├── raw/                Datos descargados tal cual llegan de AEMET, SiAR y MITECO
│   ├── interim/             Datos intermedios, todavía en proceso de limpieza
│   ├── processed/          Datos ya depurados y listos para el análisis o el modelado
│   └── external/            Datos auxiliares de terceros que no forman parte del flujo ETL principal
│
├── database/               Todo lo relativo al almacenamiento en MySQL
│   ├── schema/              Scripts de creación de tablas y relaciones
│   └── etl_apache_hop/      Transformaciones y jobs de Apache Hop
│
├── notebooks/              Cuadernos Jupyter de exploración, numerados y con las iniciales del autor
│
├── src/                    Código Python reutilizable del proyecto
│   ├── data/                 Extracción y carga de datos desde las APIs
│   ├── features/             Construcción de variables (evapotranspiración, retardos, medias móviles...)
│   ├── models/                Entrenamiento, comparación y evaluación de modelos predictivos
│   ├── dss/                    Lógica de recomendación del sistema de apoyo a la decisión
│   └── visualization/       Funciones de apoyo para generar gráficos y figuras
│
├── models/                 Modelos entrenados y serializados
│
├── results/                Resultados generados por el proyecto
│   ├── figures/              Gráficos y figuras finales
│   └── reports/              Informes de evaluación, métricas y análisis
│
├── dashboards/              Cuadros de mando (Power BI o Tableau)
│
├── docs/                    Documentación del TFM
│   ├── anteproyecto/         Anteproyecto y propuesta inicial del proyecto
│   ├── memoria/                Memoria del TFM en curso
│   ├── entregables_modulos/  Entregas de las distintas prácticas del máster
│   └── figuras/               Imágenes utilizadas en la documentación
│
├── references/              Material de apoyo bibliográfico
│   └── bibliografia/          Registro de citas y referencias en formato APA
│
├── tests/                   Comprobaciones automáticas del código
├── docker/                  Ficheros de contenedor para el entorno reproducible
├── .github/workflows/       Automatizaciones (integración continua)
│
├── .gitignore
├── environment.yml
├── requirements.txt
├── ORGANIZACION_Y_VERSIONADO.md
└── README.md
```

## Entorno de desarrollo y tecnologías

El proyecto distingue entre tecnologías ya utilizadas en el prototipo y componentes previstos en la arquitectura final:

- Implementado: Python, pandas y NumPy para extracción, normalización, calidad y preparación; scikit-learn y XGBoost para modelado; Matplotlib para evidencias; Streamlit para la aplicación de demostración del DSS; Jupyter y Visual Studio Code para desarrollo; Git y GitHub para versionado.
- Diseñado o previsto: MySQL para persistencia relacional, Apache Hop para orquestación visual, Power BI o Tableau para presentación y Docker para despliegue reproducible.
- Condicional: PySpark solo si una futura ampliación nacional y multianual justifica procesamiento distribuido; no es necesario para el piloto actual.

Para reproducir el entorno de Python se puede usar indistintamente `environment.yml` (conda) o `requirements.txt` (pip y entornos virtuales). Se recomienda trabajar siempre dentro de un entorno virtual propio del proyecto para evitar conflictos de versiones entre los distintos miembros del equipo.

## Cómo empezar

1. Clonar el repositorio.
2. Crear el entorno virtual con `conda env create -f environment.yml` o con `python -m venv venv` seguido de `pip install -r requirements.txt`.
3. Copiar `config/.env.example` como `.env` y rellenar las claves de las APIs necesarias (este fichero nunca se sube al repositorio).
4. Consultar `ORGANIZACION_Y_VERSIONADO.md` para conocer las normas de trabajo en equipo antes de empezar a programar.
5. Comprobar el acceso a SiAR con `python -m src.data.siar_client`. El comando solo muestra los contadores y límites de uso; nunca imprime el token.
6. Ejecutar una extracción piloto con `python -m src.data.extract_pilot`. Por defecto descarga siete días de `AL01` y las predicciones de Almería (`04013`) en `data/raw`. Los catálogos se solicitan por separado con `--include-siar-catalogs` o `--include-aemet-catalogs`; puede añadirse `--catalogs-only` para no repetir las series y respetar las cuotas.
7. Descargar un histórico SiAR sin superar su cuota con `python -m src.data.extract_siar_history --start-date 2025-05-01 --end-date 2025-09-30`. El proceso divide automáticamente el periodo en bloques, espera entre peticiones y crea un único archivo raw deduplicado.
8. Descargar desde la web de necesidades netas el CSV del cultivo y guardarlo en `data/external` junto con un fichero `.metadata.json`. El repositorio incluye una [muestra normalizada del ciclo de pimiento](docs/data_samples/siar_necesidades_pimiento_AL01_2025_sample.csv) y una [plantilla de metadatos](docs/data_samples/siar_necesidades_pimiento_AL01_2025.metadata.example.json).
9. Normalizar las fuentes con `python -m src.data.transform_interim`. Si hay más de un histórico SiAR o CSV de cultivo, indicar `--siar-weather-file` y `--crop-needs-file`; no se eligen por fecha de modificación. Se verifica que estación y campaña sean compatibles. El proceso genera las tablas de clima SiAR, necesidades hídricas del cultivo, predicciones AEMET y su resumen de calidad en `data/interim`.
10. Regenerar el ejemplo visual con `python -m src.visualization.build_etl_visual`.
11. Auditar los volúmenes de las capas con `python -m src.analysis.build_etl_audit_4_1`. El resultado muestra cuántas filas entran en raw, cuántas se conservan tras la normalización y cuántas son válidas para modelar.
12. Construir el conjunto modelable en `data/processed` con `python -m src.features.feature_engineering` y generar el análisis exploratorio con `python -m src.analysis.build_eda_4_2`.
13. Entrenar y comparar Persistencia, Ridge, Random Forest, KNN, SVR y XGBoost con `python -m src.models.train_evaluate`.
14. Reentrenar por cultivo y estación con los nueve CSV oficiales disponibles de 2025–2026 mediante `python -m src.models.retrain_cases_2026`. Produce [métricas por caso](docs/data_samples/model_retraining_2026.json), [predicciones de prueba](docs/data_samples/model_predictions_retraining_2026.csv) y [comparación visual](docs/images/model_retraining_2026.png); los seis artefactos ajustados se guardan localmente en `models/retrained_2026` y no alimentan Streamlit.
15. Obtener una recomendación de riego con `python -m src.dss.recommend --fecha 2025-06-28 --horizonte 7 --superficie 1.5`. La salida diaria y el resumen se guardan en CSV y JSON en `results/reports`. Este paso puede ejecutarse sin nuevas credenciales utilizando el CSV oficial versionado.
16. Abrir la aplicación de demostración con `streamlit run src/dss/app_streamlit.py`. Para compartirla mediante un enlace público, seguir la [guía de despliegue en Streamlit Community Cloud](docs/STREAMLIT_DESPLIEGUE.md). La interfaz permite escoger entre tres casos SiAR de 2025 y seis de 2026; los CSV guardados se pueden explorar sin claves. El botón de consulta actual descarga SiAR sin token y requiere `AEMET_API_KEY` para incorporar la previsión AEMET. Si no se dispone de Streamlit, abrir la [demostración local](docs/DEMO_TFM.md) con `python -m scripts.demo_local`; utiliza el mismo motor y permite probar el caso piloto en el navegador.
17. Regenerar la validación del sistema, sus tablas y figuras con `python -m src.analysis.build_validation_5_3` y el esquema del motor con `python -m src.visualization.build_dss_visual`.
18. Ejecutar las pruebas automáticas con `python -m unittest discover -s tests`.

Las fuentes, variables y controles de calidad del apartado 3.1 se sintetizan en [`docs/memoria/03_01_fuentes_variables_calidad_datos.md`](docs/memoria/03_01_fuentes_variables_calidad_datos.md). Los inventarios técnicos completos se mantienen en [`docs/FUENTE_DATOS_SIAR.md`](docs/FUENTE_DATOS_SIAR.md), [`docs/FUENTE_DATOS_AEMET.md`](docs/FUENTE_DATOS_AEMET.md) y en el [catálogo de variables](docs/data_samples/feature_catalog_4_2.csv), evitando duplicar diccionarios.
Para reconstruir los resultados sin tokens desde un clon limpio, seguir [`docs/REPRODUCCION_PILOTO.md`](docs/REPRODUCCION_PILOTO.md). El repositorio incluye solo las entradas públicas necesarias del piloto; las demás extracciones siguen excluidas.
Para repetir exactamente el entorno principal comprobado, instalar [`requirements-piloto.txt`](requirements-piloto.txt). La [auditoría de coherencia](docs/AUDITORIA_COHERENCIA_2026-10-22.md) distingue las correcciones verificadas de las limitaciones aún abiertas.
La arquitectura, las tecnologías y el flujo de información del apartado 3.2 están en [`docs/memoria/03_02_arquitectura_tecnologias_flujo.md`](docs/memoria/03_02_arquitectura_tecnologias_flujo.md), con su [figura reproducible](docs/images/arquitectura_sistema_3_2.png) y el código que la genera en `src/visualization/build_architecture_visual.py`.
La selección y el tratamiento conjunto de los datos de SiAR y AEMET se documentan en [`docs/ESTRATEGIA_DATOS_DSS.md`](docs/ESTRATEGIA_DATOS_DSS.md).
Los resultados y las incidencias de la primera carga real se recogen en [`docs/PRIMERA_EXTRACCION_PILOTO.md`](docs/PRIMERA_EXTRACCION_PILOTO.md).
El texto desarrollado del apartado 4.1 y su ejemplo visual están en [`docs/memoria/04_01_extraccion_transformacion_almacenamiento.md`](docs/memoria/04_01_extraccion_transformacion_almacenamiento.md).
El desglose reproducible de volumen y calidad está en [`docs/data_samples/etl_volume_summary_4_1.csv`](docs/data_samples/etl_volume_summary_4_1.csv).
El texto desarrollado del apartado 4.2 y el código de preparación de variables están en [`docs/memoria/04_02_analisis_exploratorio_preparacion_variables.md`](docs/memoria/04_02_analisis_exploratorio_preparacion_variables.md) y `src/features/feature_engineering.py`.
El resumen de la sesión del apartado 4.2 está en [`docs/RESUMEN_SESION_2026-09-28_LUISM.md`](docs/RESUMEN_SESION_2026-09-28_LUISM.md).
El desarrollo, los resultados y el resumen del apartado 4.3 están en [`docs/memoria/04_03_desarrollo_evaluacion_modelo_predictivo.md`](docs/memoria/04_03_desarrollo_evaluacion_modelo_predictivo.md), [`docs/data_samples/model_evaluation_4_3.json`](docs/data_samples/model_evaluation_4_3.json) y [`docs/RESUMEN_SESION_2026-09-28_LUISM_4_3.md`](docs/RESUMEN_SESION_2026-09-28_LUISM_4_3.md).

La ampliación reproducible a maíz y algodón, con sus métricas y figuras, está en [`docs/EVALUACION_MAIZ_ALGODON_2025.md`](docs/EVALUACION_MAIZ_ALGODON_2025.md).
La incorporación inicial de AEMET al motor, las pruebas de escenario y la captura de previsiones emitidas se describen en [`docs/INTEGRACION_AEMET_DSS.md`](docs/INTEGRACION_AEMET_DSS.md).
El cierre conjunto de los capítulos 3 y 4 tras la revisión del tutor se recoge en [`docs/RESUMEN_SESION_2026-10-07.md`](docs/RESUMEN_SESION_2026-10-07.md).
El diseño del motor de recomendación, la aplicación y la validación del capítulo 5 están en [`docs/memoria/05_01_diseno_sistema_recomendacion.md`](docs/memoria/05_01_diseno_sistema_recomendacion.md), [`docs/memoria/05_02_aplicacion_visualizacion_resultados.md`](docs/memoria/05_02_aplicacion_visualizacion_resultados.md) y [`docs/memoria/05_03_validacion_resultados_analisis_critico.md`](docs/memoria/05_03_validacion_resultados_analisis_critico.md), con el informe reproducible en [`docs/data_samples/dss_validation_5_3.json`](docs/data_samples/dss_validation_5_3.json) y el resumen de trabajo en [`docs/RESUMEN_SESION_2026-10-12_CAPITULO_5.md`](docs/RESUMEN_SESION_2026-10-12_CAPITULO_5.md).
Las conclusiones del capítulo 6 están en [`docs/memoria/06_01_cumplimiento_objetivos_aportaciones.md`](docs/memoria/06_01_cumplimiento_objetivos_aportaciones.md), [`docs/memoria/06_02_limitaciones_impacto.md`](docs/memoria/06_02_limitaciones_impacto.md) y [`docs/memoria/06_03_mejoras_lineas_futuras.md`](docs/memoria/06_03_mejoras_lineas_futuras.md).
El estado global del TFM y la hoja de ruta priorizada se mantienen en [`docs/ESTADO_TFM_Y_TRABAJO_PENDIENTE.md`](docs/ESTADO_TFM_Y_TRABAJO_PENDIENTE.md).

La forma de trabajar con ramas, commits, push y pull requests se explica en [`CONTRIBUTING.md`](CONTRIBUTING.md). La justificación metodológica para la memoria está en [`docs/memoria/03_03_planificacion_organizacion_proyecto.md`](docs/memoria/03_03_planificacion_organizacion_proyecto.md).

## Datos sensibles
No se almacenan en este repositorio credenciales, contraseñas ni claves de acceso a las APIs. Las variables de entorno se gestionan mediante un fichero `.env` local que queda excluido por el `.gitignore`.
