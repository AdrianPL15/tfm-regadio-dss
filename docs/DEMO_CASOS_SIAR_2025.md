# Casos SiAR incluidos en la demostración

La aplicación pública permite cambiar entre tres combinaciones concretas de comunidad, provincia, cultivo y estación. Cada combinación selecciona **su propio CSV diario oficial de necesidades netas**; el motor de recomendación es el mismo. La interfaz no descarga automáticamente datos para cualquier opción de España: solo ofrece los casos versionados en `data/external`.

| Comunidad | Provincia | Cultivo | Estación SiAR | Periodo 2025 | Filas del CSV | Kc distintos |
|---|---|---|---|---|---:|---:|
| Andalucía | Almería | Pimiento | AL01 La Mojonera | 01/05–30/09 | 150 | 5 |
| Aragón | Zaragoza | Maíz | Z06 Ejea de los Caballeros | 01/04–30/09 | 183 | 6 |
| Extremadura | Badajoz | Algodón | BA08 Don Benito | 01/04–30/09 | 183 | 5 |

Los dos CSV nuevos se descargaron el 23/10/2026 desde [«Cálculo de necesidades netas» de SiAR](https://servicio.mapa.gob.es/siarweb/necesidadesHidricas/calculo), seleccionando datos **diarios** y los filtros exactos de la tabla. Los ZIP descargados contienen los CSV directos, preservados sin transformar. Cada CSV tiene un `.metadata.json` homónimo con fecha, estación, comarca, cultivo, ciclo y número de registros. El CSV de pimiento ya estaba versionado, con algunas fechas y observaciones ausentes documentadas en sus metadatos.

Los encabezados de los nuevos CSV (`ET0`, `ETc`, `Pe`, `ETc - Pe`) no incluyen «(mm)», a diferencia de la instantánea inicial de pimiento. El lector acepta ambos esquemas y convierte las columnas a las mismas variables internas. En SiAR, el valor total publicado para «ETc - Pe» resta los totales de ETc y Pe; **no equivale necesariamente a la suma de las necesidades diarias no negativas del CSV**, ya que en días lluviosos la necesidad diaria se trunca a cero. Para auditar una suma diaria deben usarse las filas, no esa diferencia agregada.

El cambio de cultivo o estación muestra que la lógica puede aplicarse a datos de otras zonas. **No demuestra que los modelos predictivos se hayan reentrenado ni evaluado con esos cultivos.** Las métricas de evaluación documentadas en el TFM siguen referidas al piloto pimiento–AL01. Tampoco puede inferirse del CSV el sistema de producción concreto ni el riego realmente aplicado en parcela. El resultado es una recomendación orientativa retrospectiva, no una validación agronómica de las dosis.

Para verificar los casos sin claves: ejecutar `python -m unittest discover -s tests` desde la raíz del repositorio y abrir `streamlit run src/dss/app_streamlit.py`. Elegir cada comunidad en la barra lateral y observar cómo cambian el CSV, la estación y la recomendación. La guía de despliegue está en [STREAMLIT_DESPLIEGUE.md](STREAMLIT_DESPLIEGUE.md).
