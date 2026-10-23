# Publicación de la demostración Streamlit

La app ya utiliza el CSV oficial versionado para el caso piloto y no necesita claves de SiAR ni AEMET. La memoria del TFM muestra una captura, pero el enlace de Streamlit permite al tutor cambiar parámetros y descargar una recomendación real.

## Configuración de publicación

La persona con permisos de administrador del repositorio debe entrar en [Streamlit Community Cloud](https://share.streamlit.io/), conectar su cuenta de GitHub y elegir:

| Campo | Valor |
|---|---|
| Repositorio | `al1sr/tfm-regadio-dss` |
| Rama | `main`, después de fusionar la PR del despliegue |
| Archivo principal | `src/dss/app_streamlit.py` |
| Versión de Python | 3.12, si la interfaz permite elegirla |
| Dependencias | `src/dss/requirements.txt` (detectado junto al archivo principal) |
| Secretos | Ninguno para la demostración |

La rama principal contiene también `environment.yml` y `requirements.txt` para el TFM completo. Streamlit busca primero un archivo de dependencias en el directorio de la app, por lo que `src/dss/requirements.txt` limita la instalación del despliegue a cuatro bibliotecas. No publicar `.env` ni introducir tokens en el panel de secretos: la demo no los usa.

## Comprobación antes de compartir el enlace

1. Abrir la URL pública que genera Streamlit y verificar que carga sin errores.
2. Confirmar los valores iniciales para el 28/06/2025, horizonte de siete días, goteo, eficiencia 0,90 y 1,5 ha: **39,0 mm netos**, **43,3 mm brutos** y **649 m³** en pantalla. El motor conserva mayor precisión: 38,96 mm, 43,29 mm y 649,4 m³.
3. Cambiar el sistema de riego o la eficiencia; comprobar que cambia la dosis bruta, pero no la necesidad neta estimada.
4. Activar una dotación semanal de 20 mm y comprobar el aviso o ajuste de la recomendación.
5. Descargar el CSV y abrir el desplegable de reglas aplicadas.
6. Abrir la URL en una sesión privada del navegador para verificar que el tutor puede acceder sin iniciar sesión.

Cuando esas comprobaciones pasen, colocar la URL pública en la primera pantalla del `README.md` y en el anexo de la memoria. No se debe inventar la URL antes de que Streamlit la confirme.

**Alcance:** el prototipo es retrospectivo y se limita al pimiento en la estación AL01 durante 2025. Su encuadre como cultivo al aire libre queda pendiente de acreditar para el CSV empleado. La referencia SiAR no es riego real observado. No demuestra ahorro de agua ni validez agronómica fuera del piloto.
