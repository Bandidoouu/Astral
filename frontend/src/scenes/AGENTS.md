# Hanna: visualización

Tu ámbito de escritura es exclusivamente esta carpeta y sus subcarpetas.
Continúa la implementación existente; no reemplaces la aplicación completa.

## Responsabilidades

Globos Tierra/Luna/Marte, cámara, selección geográfica, marcadores, arcos,
capas con datos oficiales, galaxia UMAP y futuro detalle de relieve.
Los recursos importados pueden vivir en `assets/`; los estilos propios en
[scenes.css](scenes.css), con selectores locales prefijados `astral-`.

## Interfaz con Violeta

Conserva los exports [index.ts](index.ts): `PlanetaryScene` y `LunarSuitabilityMap`.
Implementa los props de [../shared/visualization.ts](../shared/visualization.ts).
Ese archivo es de lectura para tu tarea, al igual que API, UI, mocks y configuración.
No cambies esos tipos ni instales dependencias sin coordinar la integración.
No importes componentes ni CSS de UI.
Devuelve selecciones mediante `onSelect({ body, lat, lon })`, en grados:
latitud [-90, 90], longitud este-positiva [-180, 180].
Respeta `view` (system o galaxy), `resetKey` y los datos recibidos.
`focusedMatch` enfoca una coincidencia y `onInspect` notifica clics en sus marcadores. No recalcules rankings ni hagas
peticiones a la API dentro de las escenas.

## Estado y pendientes

- El atlas usa [orbitLayout.ts](orbitLayout.ts) y [OrbitalGuides.tsx](OrbitalGuides.tsx):
  composición fija con Luna cerca de Tierra, anillos visuales continuos y
  conexiones de analogía discontinuas. Por corrección del usuario se retiraron
  Sol, animación orbital, períodos y Distance scale. No reintroducirlos.
  No son posiciones reales ni tamaños a escala. Probar en escritorio y dejar
  el navegador en formato de computadora al terminar.

- Hay tres globos esquemáticos seleccionables, órbita, marcadores y arcos.
- Galaxia dibuja los puntos recibidos; demo solo tiene cuatro puntos a 60 m.
- [LunarSuitabilityMap.tsx](LunarSuitabilityMap.tsx) presenta un PNG polar exportado.
  El PNG incluye figura/leyenda y no tiene bounds para proyectarlo sobre la esfera.
  No usarlo como textura geográfica ni inventar coordenadas.
- Capas científicas sobre el globo y relieve real siguen pendientes.
  El enfoque de cámara al seleccionar coincidencias ya está implementado.
  El detalle de relieve necesita antes un contrato de datos coordinado.
- No simules datos científicos. Antes de descargar fuentes nuevas, coordina su
  registro en la documentación de datos según las reglas generales.
- Conserva fallback sin WebGL; no bloquees el formulario si falla el canvas.
- Prueba selección, cambio de vista, reset de cámara y datos vacíos. Ejecuta
  `npm test` y `npm run build` desde frontend sin modificar archivos ajenos.
