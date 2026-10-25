# Demostración comprobable del TFM — consulta actual y piloto histórico

La presentación principal usa la [aplicación pública Streamlit](https://tfm-regadio-dss-adrianpl15.streamlit.app/). Debajo queda una alternativa local sin tokens, basada en el piloto retrospectivo de 2025. Las dos interfaces llaman al mismo motor de `src/dss/engine.py`. Streamlit añade la actualización en memoria de SiAR, la predicción municipal de AEMET y la comparación con los modelos de ETc reentrenados.

## Recorrido principal en Streamlit

1. En **Caso analizado**, elegir comunidad, provincia, cultivo, estación y campaña entre las combinaciones verificadas. Para enseñar una recomendación de mañana, escoger un cultivo que la pantalla presente como activo y con observaciones recientes. La app no permite todavía cualquier combinación española. Si ningún caso cumple la condición de actualidad en la fecha de la presentación, usar el ejemplo histórico local de más abajo y explicar esa limitación.
2. Pulsar **Actualizar fuentes y generar recomendación**. Comprobar los mensajes de SiAR y AEMET por separado. SiAR actualiza el caso vigente en memoria; el CSV de GitHub no cambia. La consulta AEMET requiere `AEMET_API_KEY` en los secretos del despliegue. Si falla una fuente, la interfaz lo avisa y puede recurrir a la instantánea guardada o mostrar una dosis sin descuento de lluvia. Una respuesta AEMET recibida también puede tener una emisión no vigente: en ese caso la app explica que no descuenta esa lluvia.
3. Mostrar primero **Riego recomendado**: dosis en L/m², volumen en m³ para la superficie indicada y equivalente en m³/ha. Una lámina de 1 mm equivale a 1 L/m². La dosis bruta incluye la eficiencia de aplicación. Los días posteriores al primero son orientativos y deben recalcularse con nuevas observaciones y previsiones.
4. Abrir **¿De dónde sale esta recomendación?**. Enseñar el último dato observado, la procedencia, el método usado, la eficiencia y la comparación entre ETc del modelo y `ET0 reciente × Kc`. En los cultivos activos el método físico se conserva cuando tuvo menor error de prueba o faltan datos para el modelo. Este control no equivale a validar el riego aplicado en campo.
5. Abrir **Ver previsión recibida de AEMET**. Distinguir probabilidad de precipitación (`precipitation_probability_pct`) de cantidad (`precipitation_mm`). Solo se descuenta lluvia con cantidad numérica y cobertura de las 24 horas del día. Una probabilidad sin cantidad no significa lluvia cero. La previsión corresponde al municipio, no a la parcela.
6. Abrir **Ver tabla detallada y reglas de cálculo** y pulsar **Descargar recomendación (CSV)**. El archivo incluye una fila por día, ET0, Kc, necesidad antes y después de la lluvia, dosis, volumen, método, reglas, avisos y procedencia. `precipitation_forecast_mm` queda vacío donde no hay cantidad aplicable. Los decimales del archivo usan punto para facilitar el análisis en Python.
7. Para enseñar el límite del ciclo, elegir **Pimiento → campaña 2026** en Almería. La pantalla debe avisar de que no hay predicción actual porque el Kc de octubre es nulo, y etiquetar el resultado disponible como **Ejemplo histórico**. Repetir si interesa con maíz en Zaragoza o algodón en Badajoz. No presentar esos ejemplos como una dosis para mañana.

### Comprobación funcional del 25/10/2026

Se probó **Andalucía → Almería → Coliflor → AL01 La Mojonera → campaña 2026**, planificación desde el 25/10/2026, siete días, goteo, eficiencia 0,90 y 1,5 ha. La app informó de SiAR actualizado hasta el 23/10 y de una previsión AEMET emitida el 24/10 a las 20:59 para el municipio `04013`. El primer día mostró **2,2 L/m²**, **33 m³** para la parcela y **2,0 mm** de necesidad neta; la lluvia cuantificada era **0,0 mm**. El CSV descargado contenía siete filas, del 25 al 31/10: **2,22 mm** y **33,306 m³** el primer día; **15,54 mm** y **233,142 m³** acumulados. La pantalla redondea los valores. Este resultado fechado no se debe esperar literalmente en otra consulta.

Para demostrar el efecto de lluvia cuando AEMET no anuncia una cantidad positiva, marcar **Explorar un escenario de lluvia**. Con el supuesto probado de 8 mm el primer día y 50 % aprovechable, la dosis bajó de 2,2 a 0,0 L/m². Es un escenario **hipotético**, separado de AEMET. Desmarcarlo para volver a la consulta real.

## Alternativa sin API: piloto histórico local

El ejemplo local usa el CSV oficial versionado de pimiento, estación `AL01` La Mojonera (Almería), campaña 2025. El encuadre **al aire libre** es una hipótesis que este CSV no acredita. La interfaz permite mostrar el funcionamiento del motor sin consultar SiAR ni AEMET.

### Abrir la demo local

Desde la raíz del repositorio, con el entorno virtual y las dependencias de `requirements.txt` instalados:

```powershell
python -m scripts.demo_local
```

Abrir [http://127.0.0.1:8765](http://127.0.0.1:8765). El servidor escucha solo en el propio ordenador. En el entorno `.venv` de trabajo del equipo también funciona con `& .venv/Scripts/python.exe -m scripts.demo_local`. Para detenerlo: `Ctrl+C`. Si el puerto 8765 está ocupado, debe cerrarse el otro proceso antes de arrancar este servidor.

La pantalla permite cambiar fecha, horizonte, sistema y eficiencia de riego, superficie y dotación. Recalcula mediante el motor real y muestra indicadores, gráfico, tabla, explicaciones y un CSV descargable. No es una simulación dibujada a mano. Está limitada a planificación retrospectiva del piloto y al intervalo 01/05/2025–30/09/2025; la referencia SiAR posterior no se muestra como entrada del algoritmo.

### Recorrido del piloto histórico

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
| App pública y casos verificables | [`src/dss/app_streamlit.py`](../src/dss/app_streamlit.py), [`src/dss/config.py`](../src/dss/config.py) | 5.2 |
| Modelos reentrenados y criterio de uso | [`model_retraining_2026.json`](data_samples/model_retraining_2026.json), [`etc_model_deployment_2026.json`](data_samples/etc_model_deployment_2026.json) | 4.3 y 5.1 |

La app pública es la demostración principal. También puede ejecutarse localmente con `streamlit run src/dss/app_streamlit.py` si Streamlit está instalado. La demo histórica evita depender de las APIs durante la presentación; no modifica el método de cálculo.

**Verificación:** el 25/10/2026 pasaron 33 pruebas focalizadas de la demo local, el motor, la integración AEMET y el despliegue de ETc. La prueba automatizada de la interfaz mediante Streamlit `AppTest` no concluyó en este entorno; el recorrido público anterior se comprobó manualmente en el navegador. Repetir la suite completa en el entorno definitivo.

**Alcance:** ninguna pantalla demuestra ahorro de agua, aumento de rendimiento o generalización a otros cultivos y estaciones. Los resultados se contrastan con la necesidad neta calculada por SiAR, no con riegos realmente aplicados ni datos de campo.
