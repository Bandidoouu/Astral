# Hanna + Violeta

## Carpeta de cada una

- Hanna: [src/scenes/](src/scenes/). Globos, cámara, selección geográfica, arcos,
  capas, galaxia, relieve, visualización polar y recursos propios.
- Violeta: [src/ui/](src/ui/). Formularios, tarjetas, radar, estados, pesos,
  atributos, límites, idiomas y estilos de la interfaz.
- Compartido: API, fixtures, tipos, composición y configuración.
  Ver el mapa exacto en [AGENTS.md](AGENTS.md).

La UI recibe los renderizadores mediante props. Hanna puede reorganizar internamente
su carpeta mientras mantenga los exports y props acordados.
Una nueva vista o nuevo evento requiere acordar el cambio de interfaz compartida.

## Base común y ramas

La separación se preparó localmente en `frontend/planetary-explorer`.
Todavía debe compartirse ese estado mediante un commit/PR del integrante antes
de que Hanna lo pueda descargar; un enlace a main no contiene cambios locales.
No iniciar las dos tareas sobre copias con estructuras distintas.

Cada una usa su propio clon o worktree y una rama creada desde el mismo commit:
`frontend/hanna-3d` y `frontend/violeta-ui`. No alternar ambas ramas en una misma
carpeta de trabajo simultáneamente. Integrar con PRs pequeños y comprobar la
aplicación conjunta. Los cambios compartidos se hacen en una tarea de integración.
No agregar coautores de IA.

Desde la raíz de su clon, una vez compartida la rama base:

```sh
git fetch origin
git switch -c frontend/hanna-3d origin/frontend/planetary-explorer
git config core.hooksPath .githooks
cd frontend
npm ci
npm run dev
```

Para Violeta, cambiar únicamente el nombre de la rama a `frontend/violeta-ui`.
En PowerShell usar `npm.cmd` si se bloquea `npm.ps1`.
Antes de abrir PR: `npm test`, `npm run build`, revisar `git diff --name-only`
y confirmar que los archivos editados pertenecen a la carpeta asignada.

## Prompt para Hanna

> Estoy trabajando como Hanna en ASTRAL, en la rama frontend/hanna-3d.
> Lee las instrucciones raíz, frontend/CLAUDE.md, frontend/AGENTS.md,
> frontend/src/scenes/AGENTS.md y frontend/WORKING_TOGETHER.md.
> Continúa la visualización existente. Edita exclusivamente frontend/src/scenes/
> y sus subcarpetas; incluye ahí tus componentes, estilos y recursos.
> Soy responsable de globos, cámara, selección, arcos, capas, galaxia y relieve.
> Conserva los exports de scenes/index.ts y los props definidos en
> frontend/src/shared/visualization.ts. Puedes leer API y tipos compartidos,
> pero no modificarlos. No edites frontend/src/ui/, App.tsx, configuración,
> dependencias, backend, ML ni contratos. Si necesitas un cambio compartido,
> describe exactamente qué necesitas para que lo integremos.
> No inventes datos científicos ni proyectes el PNG polar como textura sin
> georreferenciación. Conserva el fallback sin WebGL. Ejecuta npm test y
> npm run build y reporta cambios y pendientes. No agregues autoría ni
> coautoría de IA a commits o PRs.

## Prompt para Violeta

> Trabajo como Violeta en la UI de ASTRAL. Lee las instrucciones raíz y las de
> frontend y frontend/src/ui/. Edita exclusivamente frontend/src/ui/ y sus
> subcarpetas. Continúa formularios, tarjetas, radar, estados, accesibilidad e
> idioma, usando los renderizadores recibidos por props. No edites scenes,
> API, mocks, tipos compartidos ni configuración; describe cualquier cambio
> de integración que necesites. Mantén visibles los datos faltantes, warnings,
> límites científicos y etiquetas de demo. Verifica npm test y npm run build.
> No agregues autoría ni coautoría de IA.

## Punto de continuidad

Corrección vigente (2026-11-14): las órbitas son solo guías visuales estáticas.
Se retiraron el Sol, el reloj, los períodos y Distance scale, junto con sus props
en [src/shared/visualization.ts](src/shared/visualization.ts). Hanna continúa la
composición 3D; Violeta mantiene misiones, evidencia y ficha descargable.
Probar en escritorio y dejar abierta esa vista. No cambia el contrato del backend.
Elegir una misión desde Luna/Marte dirige la búsqueda hacia Tierra.
En demo no cambia el ranking; las actividades de campo son propuestas editoriales.

Ya está implementada la UI del contrato de búsqueda entre los tres cuerpos:
destinos, escalas 1000/60, albedo, warnings, datos faltantes, patches y atributos.
Suitability tiene controles, leyenda, pesos y candidatos, con un renderer polar
separado. Demo no incluye raster lunar ni búsqueda neuronal real.

Hanna parte de globos esquemáticos con órbita/clic/arcos y galaxia de puntos.
Ya hay enfoque de cámara al seleccionar coincidencias y guías orbitales visuales.
Pendientes: capas oficiales y relieve con datos reales.
Violeta parte de la interfaz funcional; puede mejorar composición, estados,
accesibilidad y traducciones sin reconstruir la parte 3D.

El contrato nuevo procede de `main@ccc87b9`. Antes de integrar
con el backend real, verificar versión y disponibilidad de índices/artefactos.
No se ha validado todavía una búsqueda neuronal real de punta a punta.
