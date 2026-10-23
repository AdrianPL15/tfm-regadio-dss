# Demostración comprobable del TFM

Esta guía permite mostrar el prototipo sin tokens, sin llamadas a SiAR/AEMET y sin reconstruir la ETL en directo. Se usa el CSV oficial de necesidades del piloto ya versionado: pimiento, estación `AL01` La Mojonera (Almería), campaña 2025. El encuadre **al aire libre** es una hipótesis pendiente de acreditar para este CSV. La demo consulta el **mismo** `src/dss/engine.py` que la aplicación Streamlit y la línea de comandos.

## Abrir la demo local

Desde la raíz del repositorio, con el entorno virtual y las dependencias de `requirements.txt` instalados:

```powershell
python -m scripts.demo_local
```

Abrir [http://127.0.0.1:8765](http://127.0.0.1:8765). El servidor escucha solo en el propio ordenador. En el entorno `.venv` de trabajo del equipo también funciona con `& .venv/Scripts/python.exe -m scripts.demo_local`. Para detenerlo: `Ctrl+C`. Si el puerto 8765 está ocupado, debe cerrarse el otro proceso antes de arrancar este servidor.

La pantalla permite cambiar fecha, horizonte, sistema y eficiencia de riego, superficie y dotación. Recalcula mediante el motor real y muestra indicadores, gráfico, tabla, explicaciones y un CSV descargable. No es una simulación dibujada a mano. Está limitada a planificación retrospectiva del piloto y al intervalo 01/05/2025–30/09/2025; la referencia SiAR posterior no se muestra como entrada del algoritmo.

## Recorrido de cinco minutos para el tutor

1. Mantener 28/06/2025, siete días, goteo, eficiencia 0,90 y 1,5 ha. Pulsar **Calcular recomendación**. Deben verse **38,96 mm netos**, **43,29 mm brutos** y unos **649 m³**. Mostrar el salto del coeficiente `Kc` de 0,70 a 0,90 el 1 de julio en la tabla. Corresponde al ejemplo del apartado 5.2 de la memoria.
2. Cambiar el sistema a aspersión: la necesidad neta no cambia, pero sí la dosis bruta y el volumen porque cambia la eficiencia orientativa a 0,75.
3. Volver a goteo y establecer una dotación de 20 mm. Mostrar cómo el motor reduce la propuesta y explica la regla aplicada; **no** implica que 20 mm sea una dotación agronómicamente correcta.
4. Descargar el CSV. Abrir las explicaciones para distinguir necesidad estimada, ajuste de eficiencia y restricciones.
5. Enseñar las pruebas y las evidencias: `python -m unittest discover -s tests -q`, `docs/data_samples/etl_volume_summary_4_1.csv`, `docs/data_samples/model_evaluation_4_3.json` y `docs/data_samples/dss_validation_5_3.json`.

## Correspondencia con el repositorio y la memoria

| Qué se enseña | Evidencia | Apartado |
|---|---|---|
| Volumen de la ETL: 150 filas raw por fuente SiAR y 148 etiquetas válidas | `docs/data_samples/etl_volume_summary_4_1.csv`, `src/analysis/build_etl_audit_4_1.py` | 4.1 |
| Comparación de seis enfoques; la persistencia gana en este piloto | `docs/data_samples/model_evaluation_4_3.json`, `src/models/train_evaluate.py` | 4.3 |
| Recomendación interactiva | `scripts/demo_local.py`, `docs/demo/index.html`, `src/dss/engine.py` | 5.1–5.2 |
| Validación técnica, 13 escenarios y errores por horizonte | `docs/data_samples/dss_validation_5_3.json`, `src/analysis/build_validation_5_3.py` | 5.3 |

La interfaz Streamlit original sigue disponible con `streamlit run src/dss/app_streamlit.py` **si Streamlit está instalado**. La demo local evita esa dependencia de presentación, no reemplaza ni modifica el método de cálculo.

**Alcance:** ninguna pantalla demuestra ahorro de agua, aumento de rendimiento o generalización a otros cultivos y estaciones. Los resultados se contrastan con la necesidad neta calculada por SiAR, no con riegos realmente aplicados ni datos de campo.
