# Publicación de la demostración Streamlit

La app utiliza el CSV oficial versionado para el caso piloto y no necesita claves de SiAR ni AEMET. La demo está publicada en [Streamlit Community Cloud](https://tfm-regadio-dss-adrianpl15.streamlit.app/); permite al tutor cambiar parámetros y consultar una recomendación real.

## Configuración de publicación

El despliegue se creó el 23/10/2026 desde el fork de Adrián en [Streamlit Community Cloud](https://share.streamlit.io/) con esta configuración:

| Campo | Valor |
|---|---|
| Repositorio | `AdrianPL15/tfm-regadio-dss` (fork de `al1sr/tfm-regadio-dss`) |
| Rama | `main` |
| Archivo principal | `src/dss/app_streamlit.py` |
| Versión de Python | 3.12 |
| Dependencias | `src/dss/requirements.txt` (detectado junto al archivo principal) |
| Secretos | Ninguno para la demostración |
| URL pública | `https://tfm-regadio-dss-adrianpl15.streamlit.app/` |

La rama principal contiene también `environment.yml` y `requirements.txt` para el TFM completo. Streamlit busca primero un archivo de dependencias en el directorio de la app, por lo que `src/dss/requirements.txt` limita la instalación del despliegue a cuatro bibliotecas. No publicar `.env` ni introducir tokens en el panel de secretos: la demo no los usa.

## Comprobación del despliegue

1. Abrir la URL pública y verificar que carga sin errores. **Comprobado el 23/10/2026** también desde un navegador separado sin iniciar sesión.
2. Confirmar los valores iniciales para el 28/06/2025, horizonte de siete días, goteo, eficiencia 0,90 y 1,5 ha: **39,0 mm netos**, **43,3 mm brutos** y **649 m³** en pantalla. El motor conserva mayor precisión: 38,96 mm, 43,29 mm y 649,4 m³.
3. Cambiar el sistema de riego a aspersión. **Comprobado:** 39,0 mm netos sin cambio y 52,0 mm brutos con eficiencia de 0,75.
4. Activar una dotación semanal de 20 mm. **Comprobado:** la dosis bruta se limita a 20,0 mm y se muestra una advertencia de déficit.
5. Abrir el desplegable de reglas aplicadas. **Comprobado:** explica ET0, Kc, eficiencia y volumen por día.
6. Descargar y abrir el CSV para verificar su contenido antes de la entrega; el botón está disponible, pero esta comprobación del fichero sigue pendiente.

La URL figura en la primera pantalla del `README.md`. Falta incorporarla al anexo de la versión final de la memoria, junto con una fecha de consulta y la advertencia de alcance del piloto. Si la app se suspende por inactividad, puede tardar unos segundos en reactivarse.

**Alcance:** el prototipo es retrospectivo y se limita al pimiento en la estación AL01 durante 2025. Su encuadre como cultivo al aire libre queda pendiente de acreditar para el CSV empleado. La referencia SiAR no es riego real observado. No demuestra ahorro de agua ni validez agronómica fuera del piloto.
