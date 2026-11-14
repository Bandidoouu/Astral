# Violeta: interfaz

Tu ámbito de escritura es esta carpeta y sus subcarpetas.
Aquí viven [ExplorerApp.tsx](ExplorerApp.tsx), componentes, estilos e idioma.
Responsabilidades: navegación, perfiles, coordenadas, destinos, escalas, tarjetas,
radar, estados, explicación de coincidencias, accesibilidad y presentación lunar.

La composición vigente prioriza el mapa a pantalla completa: cabecera compacta,
franja de coincidencias y paneles superpuestos plegables. No volver a colocar
el canvas dentro de una tarjeta pequeña ni desmontarlo al abrir datos.
Ver [README.md](README.md) para el flujo y las comprobaciones del diseño.

Recibe los renderizadores a través de los props de
[../shared/visualization.ts](../shared/visualization.ts). No importes implementaciones
de escenas. No edites la carpeta de Hanna, API, mocks, configuración ni tipos
compartidos en una tarea individual; documenta cualquier integración necesaria.

- Texto público en inglés; traducción opcional bajo [i18n/](i18n/).
- Mantén null como No data; nunca lo conviertas a cero.
- Conserva el orden de resultados del backend por destino: score no es el ranking.
- Muestra warnings, escala, pesos disponibles, atributos y not_comparable.
- No calcules similitud, pesos o mediciones científicas en la UI.
- Conserva avisos visibles de demo, estados de error y el aviso de suitability.
- Evita reglas CSS globales que alteren internos de la visualización.
- Verifica formularios, móvil, teclado, estados vacíos/error, npm test y npm run build.
