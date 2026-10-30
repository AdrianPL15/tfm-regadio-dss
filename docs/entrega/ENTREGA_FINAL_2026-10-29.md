# Guía de la entrega del TFM

Estado reproducible de la entrega: etiqueta
[`v1.0.7-entrega-final`](https://github.com/AdrianPL15/tfm-regadio-dss/tree/v1.0.7-entrega-final)
de la rama `main`. Esta referencia fija el código, los artefactos y las
evidencias utilizados en la memoria.

Fecha de última comprobación técnica: 30 de octubre de 2026.

## Archivos que se presentan

1. [Memoria definitiva en PDF](../memoria/TFM_entrega_final_2026-10-29.pdf) y [Word editable](../memoria/TFM_entrega_final_2026-10-29.docx). Incluye portada, resumen, Abstract y Keywords en inglés, índices, capítulos 1 a 6, referencias y anexo de reproducción. El equipo debe leer el PDF antes de enviarlo a la universidad.
2. [Aplicación pública Streamlit](https://tfm-regadio-dss-adrianpl15.streamlit.app/) y [recorrido de demostración](DEMO_TFM.md). El evaluador puede escoger entre los casos SiAR verificados, actualizar SiAR y AEMET, consultar una dosis y descargar el CSV.
3. [Repositorio de entrega](https://github.com/AdrianPL15/tfm-regadio-dss). El [README](../../README.md) lleva directamente a la memoria, la app, el código y las evidencias.

## Evidencias principales

| Qué se contrasta | Archivo |
|---|---|
| Extracción y limpieza del piloto: 150 registros SiAR por fuente, 148 etiquetas válidas | [Volumen de la ETL](../data_samples/etl_volume_summary_4_1.csv) y [código](../../src/data/) |
| Modelos del piloto de pimiento de 2025 | [Evaluación del apartado 4.3](../data_samples/model_evaluation_4_3.json) |
| Explicabilidad de Random Forest y XGBoost en el tramo temporal reservado | [Informe XAI](../data_samples/xai_analysis_4_3.json), [importancias](../data_samples/xai_feature_importance_4_3.csv) y [figura](../images/model_xai_4_3.png) |
| Instantánea de evaluación cerrada el 22/10/2026: seis combinaciones, 1776 filas CSV y 1584 jornadas activas válidas | [Reentrenamiento por caso](../data_samples/model_retraining_2026.json) |
| Selección entre el modelo de ETc y `ET0 reciente × Kc` para la dosis | [Comparación por caso](../data_samples/etc_model_deployment_2026.json) y [código](../../src/models/train_etc_for_dss.py) |
| Predicción multianual de ET0 para siete fechas operativas (`h=2…8`) y dos horizontes técnicos adicionales | [Documento técnico](../tecnica/EXPERIMENTO_ET0_MULTIANUAL.md), [modelos](../../models/experimental_et0_multiyear/) y [evaluación completa](../data_samples/et0_multiyear_robustness.csv) |
| Monitorización prospectiva, cobertura operativa y puerta de decisión tras 30 casos | [Inferencia diaria](../../src/analysis/run_et0_prospective_daily.py), [cobertura 2026](../data_samples/et0_operational_coverage_2026.csv) y [MLOps](../tecnica/MLOPS_MONITORIZACION.md) |
| Comprobación pública específica de Z06 con 60 días solicitados | [Resultado vivo](../data_samples/et0_z06_60day_live_check.json): 13 jornadas devueltas; Ridge o respaldo según horizonte e imputaciones |
| Reglas de riego y validación retrospectiva | [Motor](../../src/dss/engine.py) y [13 escenarios](../data_samples/dss_validation_5_3.json) |
| Interfaz desplegada | [Código Streamlit](../../src/dss/app_streamlit.py) |
| Reutilización académica y operación | [Ficha del conjunto](../tecnica/DATASET_CARD.md), [principios FAIR](../tecnica/FAIR_Y_CITACION.md) y [plan MLOps](../tecnica/MLOPS_MONITORIZACION.md) |

El 30/10/2026 se ejecutaron **159 pruebas correctas**, incluidas la ausencia de fuga temporal, el protocolo multicaso, XAI, ET0 h=1…9, monitorización prospectiva y las dos pruebas `AppTest` de Streamlit. La suite terminó correctamente en el entorno Windows normal. La consulta pública depende de los datos SiAR y AEMET disponibles en cada momento.

## Alcance que debe explicarse

- La selección se limita a seis combinaciones de cultivo y estación ya verificadas; todavía no se extrae automáticamente cualquier caso de España.
- El piloto retrospectivo de 2025 asume pimiento al aire libre. El CSV SiAR identifica «Pimiento» sin indicar el sistema productivo.
- Los modelos se compararon con necesidades calculadas por SiAR. No se registró el riego aplicado ni se midió ahorro, rendimiento o precisión en campo.
- La app estima primero la ETc antes de lluvia. Solo descuenta lluvia AEMET cuando hay milímetros horarios utilizables y aplica una fracción aprovechable **supuesta y editable**. La dosis de hoy representa la necesidad del día completo y requiere ajuste si ya se ha regado.
- La vía operativa preferente predice ET0 con Ridge multianual y la combina con el Kc conocido. Hasta acumular 30 casos prospectivos pareados se etiqueta como provisional; si faltan ventanas completas o no supera la puerta definida, se utiliza `ET0 reciente × Kc` como respaldo trazable.
- En cinco de los seis casos del experimento de ETc, el respaldo físico tuvo menor MAE de prueba que el modelo de ETc seleccionado. Esa comparación no evalúa Ridge multianual extremo a extremo y no se presenta como mejora general del aprendizaje automático.
- El carácter inteligente del DSS reside en la arquitectura híbrida, la integración automatizada de fuentes, la selección trazable del método y las reglas agronómicas; comprobar que un modelo complejo no mejora de forma estable la referencia física es un resultado experimental válido.
- Los días posteriores al primero son orientativos. No hay histórico de emisiones AEMET alineadas con 2025 ni balance hídrico de la parcela para validarlos prospectivamente.
- La prioridad de evolución es un balance hídrico de parcela con sensores de humedad, propiedades del suelo y registro del riego realmente aplicado.

La [revisión cruzada](../historico/auditorias/REVISION_CRUZADA_ENTREGA_2026-10-25.md) recoge la comprobación entre memoria, código y aplicación. Las versiones anteriores de la memoria y los guiones editoriales permanecen recuperables en el historial de Git; los archivos señalados arriba son los de entrega.
