# Cierre de auditoría de la entrega

Versión `v1.0.7-entrega-final`, 30 de octubre de 2026.

## Correcciones realizadas

- El motor conserva el resultado del selector ET0 para cada fecha, incluidos el respaldo físico y la abstención. No sustituye un resultado no disponible por otra media local. Sin selector, se limita igualmente la antigüedad del respaldo a siete días. Un Kc nulo en planificación se trata como fuera de ciclo, sin una dosis aparente de cero.
- Streamlit muestra el motivo de indisponibilidad junto a los controles de fecha y en el área principal, antes de la dosis. Distingue fuera de ciclo, falta de datos actuales, consulta histórica y horizonte parcialmente fuera del calendario. Un horizonte sin días calculables se presenta como «sin datos».
- La selección de ventana excluye los objetivos del tramo reservado aunque la emisión sea anterior al corte. Las cifras de desarrollo de la Tabla 5.3 son ahora 0,525; 0,503; 0,493; 0,480 y 0,478 mm/día. Se mantiene la ventana de siete días y el MAE de prueba a un día de 0,090 mm/día.
- La puerta prospectiva decide por estación y horizonte, con 30 fechas objetivo distintas, consolidadas y pareadas como mínimo, hasta 60 fechas recientes y mejora mínima del MAE del 5 %. El agregado global queda como diagnóstico. Se conserva la instantánea prospectiva publicada previa; la siguiente ejecución diaria poblará las nuevas decisiones por grupo.
- Se corrigieron las correspondencias de las Figuras 4.5, 4.6, 4.7 y 4.8 y se sincronizó la Figura 4.9 con las evidencias SHAP. Se completaron y actualizaron los índices de tablas y figuras, incluido el anexo.
- La memoria matiza la interpretación del sesgo positivo, explica qué periodos participan en la aprobación y reajuste de ET0 y propone indicadores de adopción y valor de negocio sin atribuir ahorro no medido.
- `requirements-reproducible.txt` fija dependencias directas e indirectas para Python 3.12, con marcadores para Windows y Linux. La integración continua lo utiliza; los requisitos mínimos del despliegue siguen en `src/dss/requirements.txt`.

## Verificación

- 159 pruebas automáticas superadas con Python 3.12.4 y las versiones fijadas, incluidas pruebas de interfaz Streamlit.
- 13 de 13 escenarios del motor superados al regenerar la validación.
- Se regeneraron las figuras y la evidencia de validación afectadas; el análisis SHAP se ejecutó con el entorno fijado y conserva los valores publicados.
- Memoria exportada con Word y revisada mediante imágenes de página. Se conservan 95 páginas. La copia local de entrega y el PDF de `docs/memoria/` deben tener la misma huella SHA-256.
- `git diff --check` sin incidencias.

Estas comprobaciones no sustituyen la validación agronómica en campo, la evaluación de ahorro de agua o una muestra prospectiva suficiente. Las pruebas de interfaz verifican el código; la disponibilidad del servicio publicado y de las API depende además del despliegue y de sus proveedores.

## Reproducción

```text
python -m pip install -r requirements-reproducible.txt
python -m unittest discover -s tests
python -m src.analysis.build_validation_5_3
python -m src.analysis.build_xai_4_3
streamlit run src/dss/app_streamlit.py
```

Las métricas temporales del informe de validación dependen del equipo y no incluyen consultas de red ni renderizado de la aplicación.
