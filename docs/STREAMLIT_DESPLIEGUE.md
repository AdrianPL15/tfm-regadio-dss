# Publicación de la demostración Streamlit

La app conserva tres casos SiAR de 2025 para la evaluación retrospectiva y añade seis CSV de 2026 ([inventario](CAMPANAS_SIAR_2026.md)). La consulta AEMET actual requiere su API key configurada como secreto. La demo está publicada en [Streamlit Community Cloud](https://tfm-regadio-dss-adrianpl15.streamlit.app/); permite escoger comunidad, provincia, cultivo, estación y campaña solo entre las combinaciones descargadas. En octubre de 2026 hay tres ejemplos con Kc positivo en regiones distintas: coliflor (Almería), alfalfa (Zaragoza) y alcachofa (Badajoz). La interfaz preselecciona un cultivo con observación reciente cuando existe. La estimación de mañana se ofrece únicamente cuando la campaña sigue activa y el último dato SiAR es reciente; si no, se avisa de que solo hay un ejemplo histórico.

La pantalla separa la **dosis del primer día** de la **suma provisional de hasta siete días**. Expresa la primera en mm, L/m², m³/ha y m³ para la superficie introducida (`1 mm = 1 L/m² = 10 m³/ha`). El acumulado no debe interpretarse como una orden de riego para toda la semana: el Kc futuro es una proyección limitada al mes, la ET0 se estima a partir de observaciones recientes y AEMET puede no publicar mm completos para todos los días. El botón **Actualizar fuentes y generar recomendación** consulta el CSV diario SiAR del caso 2026 seleccionado, lo compara con el histórico guardado y, si el cultivo sigue en campaña, consulta la predicción AEMET. La nueva descarga SiAR se usa **solo en la sesión de la app**: no escribe en GitHub ni reemplaza el CSV versionado. Si SiAR falla o revisa jornadas previas, se muestra un aviso y se conserva la instantánea guardada. Si falla AEMET, se muestra la dosis base sin descontar lluvia prevista. Para los casos retrospectivos de 2025 no se aplica la predicción meteorológica actual.

La app también carga seis modelos reentrenados de ETc previa a lluvia. Muestra
la predicción y su comparación con el cálculo físico. El modelo solo determina
la dosis principal si su MAE de prueba fue menor que el físico; esto ocurre en
algodón BA08, fuera de ciclo el 24/10/2026. En los cultivos activos se mantiene
el cálculo físico para la dosis. La lluvia AEMET se aplica después de elegir
la base y no se descuenta dos veces. Véase la
[evaluación de integración](INTEGRACION_ETC_AEMET_2026.md).

## Configuración de publicación

El despliegue se creó el 23/10/2026 desde el fork de Adrián en [Streamlit Community Cloud](https://share.streamlit.io/) con esta configuración:

| Campo | Valor |
|---|---|
| Repositorio | `AdrianPL15/tfm-regadio-dss` (fork de `al1sr/tfm-regadio-dss`) |
| Rama | `main` |
| Archivo principal | `src/dss/app_streamlit.py` |
| Versión de Python | 3.12 |
| Dependencias | `src/dss/requirements.txt`, con scikit-learn y joblib para los modelos versionados |
| Secretos | Ninguno para SiAR retrospectivo; `AEMET_API_KEY` opcional para la consulta actual |
| URL pública | `https://tfm-regadio-dss-adrianpl15.streamlit.app/` |

La rama principal contiene también `environment.yml` y `requirements.txt` para el TFM completo. Streamlit busca primero un archivo de dependencias en el directorio de la app; `src/dss/requirements.txt` contiene las bibliotecas necesarias para la interfaz y las consultas SiAR/AEMET. SiAR Web no requiere clave para este formulario; AEMET sí. No publicar `.env` ni añadir claves al repositorio. Para activar la consulta actual en Community Cloud, el administrador de la app debe abrir **App settings → Secrets** y pegar exactamente esta entrada TOML, sustituyendo el marcador por el valor actual de `AEMET_API_KEY` del `.env` local:

```toml
AEMET_API_KEY = "PEGAR_AQUÍ_LA_CLAVE_ACTUAL"
```

Guardar el secreto y reiniciar la app si no se actualiza sola. No copiar el archivo `.env` entero ni enviar la clave por chat o GitHub. Hasta entonces, la demo histórica sigue funcionando y el botón de AEMET informa de que falta la clave. AEMET [indica](https://opendata.aemet.es/centrodedescargas/novedades) que las claves nuevas caducan a los tres meses; habrá que renovarla en el panel cuando corresponda.

## Comprobación del despliegue

1. Abrir la URL pública y verificar que carga sin errores. **Comprobado el 23/10/2026** también desde un navegador separado sin iniciar sesión.
2. Para la campaña 2025 y el 28/06/2025, horizonte de siete días, goteo, eficiencia 0,90 y 1,5 ha, verificar en el bloque **panorama provisional** **39,0 mm netos**, **43,3 mm brutos** y **649 m³**. El motor conserva mayor precisión: 38,96 mm, 43,29 mm y 649,4 m³. La dosis destacada del primer día es distinta del acumulado.
3. Cambiar el sistema de riego a aspersión. **Comprobado:** 39,0 mm netos sin cambio y 52,0 mm brutos con eficiencia de 0,75.
4. Activar una dotación semanal de 20 mm. **Comprobado:** la dosis bruta se limita a 20,0 mm y se muestra una advertencia de déficit.
5. Abrir el desplegable de reglas aplicadas. **Comprobado:** explica ET0, Kc, eficiencia y volumen por día.
6. Descargar y abrir el CSV para verificar su contenido antes de la entrega; el botón está disponible, pero esta comprobación del fichero sigue pendiente.
7. Seleccionar Aragón → Zaragoza → Maíz → Z06 y Extremadura → Badajoz → Algodón → BA08. **Comprobado localmente y en el enlace público el 23/10/2026**, sin errores: para 28/06/2025, siete días y los parámetros iniciales, maíz muestra 50,4 mm netos / 56,0 mm brutos y algodón 47,9 mm netos / 53,2 mm brutos.
8. Activar el escenario manual de 8 mm y fracción hipotética del 50 %. La prueba local previa mostraba 35,0 mm netos y 38,9 mm brutos condicionados, frente a 39,0/43,3 mm de la dosis base. La consulta AEMET actual no debe modificar la campaña 2025. Queda pendiente repetir esta comprobación tras cada despliegue.

La URL figura en la primera pantalla del `README.md`. Falta incorporarla al anexo de la versión final de la memoria, junto con una fecha de consulta y la advertencia de alcance del piloto. Si la app se suspende por inactividad, puede tardar unos segundos en reactivarse.

**Alcance:** los ensayos de 2025 siguen siendo retrospectivos y los seis CSV de 2026 son instantáneas oficiales, no un catálogo nacional dinámico. Hay evaluaciones predictivas independientes por cultivo y estación, pero no un modelo común ni validación en campo. El 24/10/2026 coliflor AL01, alfalfa Z06 y alcachofa BA08 están en ciclo con Kc positivo; el Kc de mañana es una proyección local dentro del mes y el descuento de lluvia usa una fracción hipotética. Los modelos reentrenados de ETc se muestran en estos casos, pero sus errores de prueba aconsejan mantener el cálculo físico para la dosis. La predicción AEMET actual no se cruza con 2025. El sistema de producción exacto no queda acreditado por los CSV. La referencia SiAR no es riego real observado. La demo no demuestra ahorro de agua ni validez agronómica fuera del piloto.
