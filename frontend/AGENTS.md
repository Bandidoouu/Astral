# Frontend: trabajo compartido

Lee [CLAUDE.md](CLAUDE.md) y las reglas generales [../CLAUDE.md](../CLAUDE.md).
La asignación vigente de esta interfaz es **Hanna: visualización**, **Violeta: UI**.
El nombre Gris en documentos anteriores corresponde al reparto antiguo.

## Límites de edición

| Responsable | Carpeta | Trabajo |
| --- | --- | --- |
| Hanna | [src/scenes/](src/scenes/) | Globos, cámara, arcos, capas, galaxia, relieve y sus recursos/estilos locales |
| Violeta | [src/ui/](src/ui/) | Controles, tarjetas, radar, estados, presentación de datos, idioma y estilos UI |
| Integración coordinada | [src/shared/](src/shared/), [src/api/](src/api/), [src/mocks/](src/mocks/), [src/App.tsx](src/App.tsx), [src/main.tsx](src/main.tsx) | Tipos, API, fixtures y conexión entre UI y visualización |

Configuración, dependencias y lockfile también son compartidos.
Cada tarea de Hanna o Violeta debe permanecer en su carpeta. Si necesita una
modificación compartida, describe el cambio y su motivo para integrarlo de forma
coordinada; no lo hagas como parte incidental del trabajo individual.
Una tarea explícita de integración puede modificar ambos lados. Esta separación
es una regla de coordinación para personas y agentes, no un control de permisos.

- UI y escenas se conectan mediante [src/shared/visualization.ts](src/shared/visualization.ts).
- No importar implementaciones de UI desde escenas ni viceversa.
- Las escenas reciben datos y emiten eventos; API, búsqueda y selección viven fuera de ellas.
- Texto público en inglés. No inventar puntajes, pesos, mapas o georreferenciación.
- No agregar autoría/coautoría de IA a commits o PRs.
- Por instrucción del usuario: antes de editar, hacer pull de origin/main y conservar
  el trabajo local. Preferir `git pull --ff-only origin main`; si diverge, integrar
  sin reescribir historia. Un fetch por sí solo no actualiza la rama de trabajo.
- Antes de entregar: `npm test` y `npm run build` desde esta carpeta.
- Ver [WORKING_TOGETHER.md](WORKING_TOGETHER.md) para ramas y prompts.
