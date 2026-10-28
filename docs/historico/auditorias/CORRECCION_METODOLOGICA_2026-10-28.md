# Corrección metodológica final — 28 de octubre de 2026

## Alcance

Esta revisión cierra las correcciones previas al estudio multianual de ET0. Se ha comprobado la coherencia entre código, resultados versionados, figuras, memoria y recorrido de entrega.

## Cambios aplicados

- La comparación predictiva incorpora ET0 únicamente mediante retardos de 1, 3 y 7 días y medias previas de 3, 7 y 14 días. La ET0 del día objetivo continúa excluida.
- Se regeneraron el piloto de pimiento, el reentrenamiento de seis casos, la evaluación adicional de maíz y algodón y el análisis TreeSHAP.
- La comprobación multicaso del DSS se limita a jornadas activas (`Kc > 0`), reserva el 15 % cronológicamente final y añade un bootstrap pareado por bloques de siete días.
- Se sustituyó la expresión «transferencia temporal» por «comprobación cronológica», porque cada cultivo adicional solo aporta una campaña.
- La memoria explicita la dependencia estructural entre la referencia SiAR y la vía física del DSS; el error mide fidelidad al cálculo oficial, no validación agronómica independiente.
- Se retiraron las palabras clave por decisión del equipo y se actualizaron tablas, figuras, índices, enlaces y maquetación.

## Resultados principales tras la corrección

- En el piloto predictivo, persistencia conserva el menor MAE medio de validación (0,434 mm/día) y el menor MAE de prueba (0,120 mm/día). Ridge mejora al recibir ET0 histórica, pero no supera a persistencia de forma estable.
- En la comprobación del DSS con coliflor AL01, alfalfa Z06 y alcachofa BA08, el MAE agregado es 0,627 mm/día frente a 0,791 mm/día de persistencia.
- La diferencia agregada `MAE(persistencia) − MAE(DSS)` es 0,164 mm/día. El intervalo bootstrap percentil del 95 % es [0,030; 0,305] mm/día y el 99,2 % de los remuestreos favorece al DSS.
- Estos resultados no prueban ahorro de agua, adecuación a parcela ni generalización interanual.

## Verificación

- 103 pruebas no gráficas superadas dentro del entorno aislado.
- 2 pruebas `AppTest` de Streamlit superadas fuera del aislamiento local requerido por su canal interno.
- Total: 105 pruebas superadas.
- PDF final renderizado y revisado visualmente: 92 páginas.
- `git diff --check` sin errores de espacios ni marcadores de conflicto.

La versión preparada para entrega es `docs/memoria/TFM_definitivo_2026-10-27.pdf`, acompañada por el Word editable del mismo nombre.
