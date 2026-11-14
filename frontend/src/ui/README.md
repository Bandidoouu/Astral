# UI de Violeta: mapa como espacio principal

La referencia indicada por el equipo es la
[visualización de Tierra/Luna/NEO](https://github.com/diegoe-villasana/REPOSITORIONUEVO_FINAL_OFICIAL_AHORA_SI_QUE_SI/tree/main/Visualizacion)
(revisada en commit 47dfd764). Se adopta el patrón de escena a pantalla completa
y paneles translúcidos plegables, manteniendo los datos y componentes de ASTRAL.

## Composición

- [ExplorerApp.tsx](ExplorerApp.tsx) mantiene un único renderizador planetario
  montado. Abrir búsqueda, resultados, detalles, fuentes o suitability no reinicia
  la cámara ni reemplaza el canvas.
- [MapPanel](components/MapPanel.tsx) muestra un panel a la vez, con cierre y Escape.
  El panel recibe foco al abrir; devuelve el foco al control de origen al cerrar.
  No es modal: el resto del mapa continúa disponible.
- La franja inferior muestra las coincidencias en el orden devuelto por la API.
  Seleccionar una abre radar, dimensiones, límites, pesos y atributos.
  Puede ocultarse mediante el control del mapa.
- Los avisos de demo, carga, error y cobertura siguen visibles en el mapa aunque
  los paneles estén cerrados. Los errores y avisos completos se consultan en resultados.
- La vista polar vive en un panel, sin modificar la escena de Hanna.
- [styles.css](styles.css) define la distribución y los estilos UI. No contiene
  cambios de cámara, datos científicos ni estilos internos del renderer polar.

El lienzo ocupa el área bajo una cabecera de 58 px en escritorio: 93.6% de una
ventana de 1440 × 900, antes de superponer controles. En móvil la cabecera usa dos
filas, las coincidencias se desplazan horizontalmente y los paneles tienen scroll propio.

## Comprobado

Compilación y 10 pruebas existentes correctas. En navegador: selección desde la
franja, detalle con valores faltantes, cambio de origen, escala 60/1000, avisos de
cobertura, vista lunar sin datos, ocultar/restaurar franja, cierre con Escape y
restauración de foco. El mismo canvas permanece montado al abrir paneles.
Sin errores de ejecución en esas interacciones ni desbordamiento horizontal a 390 px.

Los globos del explorador siguen siendo esquemáticos. Cámara, texturas, capas y relieve pertenecen
a Hanna; los cambios compartidos se hacen como integración. No se incorporan datos
del proyecto de referencia ni se simulan predicciones nuevas.

## Interaccion y misiones

El atlas conserva orbitas visuales estaticas. Se retiraron el reloj, los periodos,
el Sol y Distance scale por indicacion del usuario. El contrato compartido mantiene
`focusedMatch` y `onInspect` para enfocar coincidencias; `view` admite system y galaxy.
Las animaciones de camara respetan reduced-motion. Validar en escritorio y dejar
el navegador en ese formato al terminar.

[missions.ts](missions.ts) contiene preguntas y propuestas de ensayos, sin pesos
ni mediciones calculadas. [components/MissionPanel.tsx](components/MissionPanel.tsx)
selecciona un perfil y destinos. [components/AnalogEvidence.tsx](components/AnalogEvidence.tsx)
explica puntajes, ausencias, límites y descarga una ficha Markdown. Usar el perfil
de la respuesta para que la ficha corresponda a los resultados recibidos.
Los portales de fuentes son contexto: no sustituyen procedencia por parche.

Comprobar seleccion de origen, enfoque y reset de camara, misiones, datos nulos,
descarga y navegacion por teclado. Referencia de escritorio: 1440 x 900.
