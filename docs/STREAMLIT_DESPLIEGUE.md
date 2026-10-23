# Publicación de la demostración Streamlit

La app utiliza CSV SiAR versionados para tres casos concretos; esa demostración retrospectiva no necesita claves. La ampliación opcional consulta AEMET actual y requiere su API key configurada como secreto. La demo está publicada en [Streamlit Community Cloud](https://tfm-regadio-dss-adrianpl15.streamlit.app/); permite al tutor escoger comunidad, provincia, cultivo y estación entre las combinaciones disponibles, cambiar parámetros y consultar una recomendación orientativa. Los [datos y límites de cada caso](DEMO_CASOS_SIAR_2025.md) están documentados por separado.

## Configuración de publicación

El despliegue se creó el 23/10/2026 desde el fork de Adrián en [Streamlit Community Cloud](https://share.streamlit.io/) con esta configuración:

| Campo | Valor |
|---|---|
| Repositorio | `AdrianPL15/tfm-regadio-dss` (fork de `al1sr/tfm-regadio-dss`) |
| Rama | `main` |
| Archivo principal | `src/dss/app_streamlit.py` |
| Versión de Python | 3.12 |
| Dependencias | `src/dss/requirements.txt` (detectado junto al archivo principal) |
| Secretos | Ninguno para SiAR retrospectivo; `AEMET_API_KEY` opcional para la consulta actual |
| URL pública | `https://tfm-regadio-dss-adrianpl15.streamlit.app/` |

La rama principal contiene también `environment.yml` y `requirements.txt` para el TFM completo. Streamlit busca primero un archivo de dependencias en el directorio de la app; `src/dss/requirements.txt` contiene las bibliotecas necesarias para la interfaz y la consulta AEMET. No publicar `.env` ni añadir claves al repositorio. Para activar la consulta actual en Community Cloud, el administrador de la app debe configurar `AEMET_API_KEY` en **App settings → Secrets**. Hasta entonces, la demo histórica sigue funcionando y el botón de AEMET informa de que falta la clave. AEMET [indica](https://opendata.aemet.es/centrodedescargas/novedades) que las claves nuevas caducan a los tres meses; habrá que renovarla en el panel cuando corresponda.

## Comprobación del despliegue

1. Abrir la URL pública y verificar que carga sin errores. **Comprobado el 23/10/2026** también desde un navegador separado sin iniciar sesión.
2. Confirmar los valores iniciales para el 28/06/2025, horizonte de siete días, goteo, eficiencia 0,90 y 1,5 ha: **39,0 mm netos**, **43,3 mm brutos** y **649 m³** en pantalla. El motor conserva mayor precisión: 38,96 mm, 43,29 mm y 649,4 m³.
3. Cambiar el sistema de riego a aspersión. **Comprobado:** 39,0 mm netos sin cambio y 52,0 mm brutos con eficiencia de 0,75.
4. Activar una dotación semanal de 20 mm. **Comprobado:** la dosis bruta se limita a 20,0 mm y se muestra una advertencia de déficit.
5. Abrir el desplegable de reglas aplicadas. **Comprobado:** explica ET0, Kc, eficiencia y volumen por día.
6. Descargar y abrir el CSV para verificar su contenido antes de la entrega; el botón está disponible, pero esta comprobación del fichero sigue pendiente.
7. Seleccionar Aragón → Zaragoza → Maíz → Z06 y Extremadura → Badajoz → Algodón → BA08. **Comprobado localmente y en el enlace público el 23/10/2026**, sin errores: para 28/06/2025, siete días y los parámetros iniciales, maíz muestra 50,4 mm netos / 56,0 mm brutos y algodón 47,9 mm netos / 53,2 mm brutos.
8. **Cambio aún no desplegado en la URL pública:** activar en la rama de integración el escenario manual de 8 mm y fracción hipotética del 50 %. La prueba local muestra 35,0 mm netos y 38,9 mm brutos condicionados, frente a 39,0/43,3 mm de la dosis base. La consulta AEMET real muestra la predicción actual, pero no modifica la campaña 2025. Tras fusionar y desplegar, repetir esta comprobación en la URL.

La URL figura en la primera pantalla del `README.md`. Falta incorporarla al anexo de la versión final de la memoria, junto con una fecha de consulta y la advertencia de alcance del piloto. Si la app se suspende por inactividad, puede tardar unos segundos en reactivarse.

**Alcance:** el prototipo es retrospectivo y ofrece tres combinaciones concretas durante 2025, no un catálogo nacional dinámico. Hay evaluaciones predictivas independientes para pimiento, maíz y algodón, pero no un modelo común ni validación en campo. El escenario de lluvia es hipotético; la predicción AEMET actual no se cruza con 2025. El sistema de producción exacto no queda acreditado por los CSV. La referencia SiAR no es riego real observado. La demo no demuestra ahorro de agua ni validez agronómica fuera del piloto.
