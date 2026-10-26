# Campañas SiAR 2026 y alcance de la predicción de mañana

El 23/10/2026 se creó la primera instantánea de seis combinaciones mediante el formulario oficial de [necesidades netas de SiAR](https://servicio.mapa.gob.es/siarweb/necesidadesHidricas/calculo). El 26/10 se repitió la descarga y se incorporaron, tras validación, las jornadas publicadas hasta el **25/10/2026**. Los CSV diarios originales se conservan en `data/external`, sin alterar ni completar valores. La instantánea operativa evoluciona con nuevas jornadas; la evaluación de modelos permanece congelada con el corte del 22/10 para no cambiar sus métricas después del análisis.

| Caso | Estación y provincia | Intervalo devuelto | Filas | Calidad | Situación el 26/10 |
|---|---|---|---:|---|---|
| Pimiento | AL01 La Mojonera, Almería | 01/05–25/10 | 178 | 177 completas; 1 sin meteorología | Fuera del ciclo May–Sep; Kc=0 en octubre |
| Coliflor | AL01 La Mojonera, Almería | 01/06–25/10 | 147 | 147 completas | Ciclo Jun–Dic; Kc=0,99 el 25/10 |
| Maíz | Z06 Ejea de los Caballeros, Zaragoza | 01/04–25/10 | 208 | 208 completas | Fuera del ciclo Abr–Sep; Kc=0 en octubre |
| Algodón | BA08 Don Benito, Badajoz | 01/04–25/10 | 208 | 207 completas; 1 sin meteorología | Fuera del ciclo Abr–Sep; Kc=0 en octubre |
| Alfalfa | Z06 Ejea de los Caballeros, Zaragoza | 01/03–25/10 | 239 | 239 completas | Ciclo Mar–Oct; Kc=0,83 el 25/10 |
| Alcachofa | BA08 Don Benito, Badajoz | 01/01–25/10 | 298 | 297 completas; 1 sin meteorología (07/07) | Ciclo Ene–Dic; Kc=0,95 el 25/10 |

Los archivos `.metadata.json` adjuntos indican lugar, cultivo, ciclo, periodo solicitado y periodo realmente devuelto. Son **instantáneas de descarga**, no una sincronización continua. Los seis CSV tienen Kc, ET0, ETc, precipitación efectiva y necesidad neta; SiAR no da aquí riegos efectivamente realizados. Las tres campañas de 2025 permanecen para reproducir sus evaluaciones temporales y no se sustituyen por las de 2026. Las jornadas incorporadas después del corte experimental amplían **la demostración operativa del motor de reglas**, pero no su conjunto de entrenamiento ni las métricas ya publicadas.

Para calcular un día posterior a la última observación en coliflor, alfalfa o alcachofa, el prototipo prolonga el último Kc oficial **solo dentro del mismo mes y del ciclo SiAR**. No atribuye a SiAR ese Kc futuro ni inventa ET0 o lluvia observadas. Combina ese supuesto con la media de ET0 observada en los siete días recientes y, cuando el usuario consulta AEMET con una clave válida, muestra la lluvia municipal prevista. Solo descuenta una cantidad prevista si el producto horario aporta milímetros utilizables y el usuario acepta una fracción aprovechable **hipotética**. Esta fracción no está calibrada con suelo, humedad ni riego real. La app distingue la dosis base de la condicionada y advierte que no equivale a una recomendación agronómica validada.

La interfaz ofrece ahora un panorama **orientativo de hasta siete días**, separado de la dosis del primer día. No extrapola Kc al mes siguiente sin una curva válida: si el horizonte cruza ese límite, los días no calculables se señalan y no se incluyen en el acumulado. El botón **Actualizar fuentes y generar recomendación** consulta en el momento el CSV SiAR del caso seleccionado y la previsión AEMET si corresponde. La descarga SiAR validada se usa en memoria para esa sesión; **no altera el CSV de GitHub**. Independientemente, se ha preparado una tarea diaria que propone versionar las nuevas jornadas en GitHub mediante PR; esa publicación solo ocurre después de revisarla y fusionarla. Un día futuro sin mm horarios de AEMET no se interpreta como cero lluvia.

### Actualización diaria de SiAR

El adaptador `src/data/refresh_siar_crop_needs.py` reproduce el formulario público de [necesidades hídricas de SiAR](https://servicio.mapa.gob.es/siarweb/necesidadesHidricas/calculo): obtiene la sesión y el token CSRF de la página, comprueba la estación, comarca, provincia, comunidad, cultivo y ciclo, solicita la tabla diaria y descarga el CSV del ZIP oficial. **No utiliza la API meteorológica documentada de SiAR ni necesita su token.** Los endpoints internos de la web pueden cambiar; un cambio de respuesta detiene la actualización y exige revisar el adaptador.

Se ejecuta desde la raíz del repositorio:

```bash
python -m pip install requests beautifulsoup4
python -m src.data.refresh_siar_crop_needs --check  # solo compara
python -m src.data.refresh_siar_crop_needs          # escribe si hay nuevas filas
```

Antes de escribir, valida los **seis casos completos**: columnas, fechas, límites básicos, identidad y ausencia de modificaciones u omisiones en jornadas ya versionadas. Si SiAR revisa una jornada antigua, la ejecución falla y no sustituye ningún caso: hay que estudiar la revisión y documentarla. Si no hay filas nuevas, no modifica los archivos. Al añadirlas, conserva el CSV original descargado, actualiza el `.metadata.json` con fecha de consulta, última jornada y número de registros, y deja el histórico de 2025 intacto. No fabrica valores para fechas que SiAR todavía no publica. Los casos adicionales se incorporaron una sola vez con `python -m src.data.seed_active_cases_2026`; los refrescos posteriores usan el mismo adaptador que los otros casos.

El flujo `.github/workflows/refresh-siar-crop-needs.yml` comprueba la campaña de 2026 a las 09:23 (hora de Madrid) y también puede lanzarse manualmente en la pestaña **Actions**. Su finalidad es conservar en GitHub una instantánea trazable, **no alimentar el botón de la app**, que consulta la web al pulsarlo. Propone los CSV y metadatos en una *pull request*, sin fusionar por sí solo. Para que GitHub Actions pueda crearla, en **Settings → Actions → General → Workflow permissions** debe estar activada la opción **Allow GitHub Actions to create and approve pull requests**. El flujo solicita permisos `contents: write` y `pull-requests: write`; si la configuración del repositorio los impide, habrá que habilitarlos. Este flujo deja de procesar al cambiar a 2027: la campaña nueva requiere revisar rangos, ciclos y archivos antes de automatizarla. La aplicación expira su caché de lectura de CSV versionados cada 15 minutos, pero la consulta desde el botón siempre solicita SiAR de nuevo.

La dosis se expresa en **mm de lámina de riego**, unidad habitual por superficie: `1 mm = 1 L/m² = 10 m³/ha`. La aplicación muestra también los m³ correspondientes a la superficie indicada por el usuario. La necesidad neta corresponde al cultivo; la dosis bruta a aplicar incorpora la eficiencia del sistema. Sin caudal, marco de plantación y emisores no puede traducirse con rigor a minutos de apertura o litros por planta.

El mismo día se archivaron localmente predicciones AEMET para Almería (`04013`), Ejea (`50095`) y Don Benito (`06044`) en `data/raw/aemet/forecast` y `data/interim/aemet/forecast`; estas instantáneas están excluidas de Git para no confundir previsiones emitidas hoy con un histórico utilizable en la evaluación de 2025. En Ejea, la respuesta diaria de AEMET usa un identificador interno negativo (`-15441`) mientras la horaria usa el código municipal `50095`: el adaptador conserva el código solicitado y comprueba que el producto horario y el nombre municipal coinciden.

**Límite metodológico:** esta incorporación amplía los datos históricos y la demostración de consulta actual, pero **no reentrena ni reevalúa los modelos de 2025 con pronósticos de 2026**. Para afirmar que AEMET mejora el modelo harán falta previsiones archivadas antes de cada fecha objetivo, de múltiples fechas y campañas, y validación temporal sin fuga de información. Los CSV identifican cultivo y estación, no sistema productivo ni parcela concreta. En octubre, maíz, algodón y pimiento son comparaciones históricas, no opciones de riego para mañana. La alfalfa deja de estar en el ciclo SiAR al pasar a noviembre, por lo que la demo no prolongará su Kc a ese mes sin nueva base metodológica.
