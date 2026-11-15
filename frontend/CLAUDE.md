# ASTRAL · Frontend

Aplican las reglas generales de [../CLAUDE.md](../CLAUDE.md), especialmente
texto público en inglés, fuentes oficiales y commits sin coautores de IA.

## Reparto vigente

**Hanna:** visualización en [src/scenes/](src/scenes/).
**Violeta:** UI en [src/ui/](src/ui/); sustituye la asignación antigua de Gris.
Lee [AGENTS.md](AGENTS.md) y [WORKING_TOGETHER.md](WORKING_TOGETHER.md).
Las tareas individuales no editan el área de la compañera ni archivos compartidos.
La composición está en [src/App.tsx](src/App.tsx); los props acordados en
[src/shared/visualization.ts](src/shared/visualization.ts).

## Contrato usado en esta implementación

Se adaptó al contrato de `origin/main`, commit `ccc87b9`,
consultado el 2026-11-14. Los contratos de main ya incluyen siete dimensiones y general.
El fixture local es una copia de contracts/similar_response.json.
Backend debe confirmar compatibilidad al integrar.

- Origen Earth/Moon/Mars; destinos explícitos `target_bodies`, distintos del origen.
- Escala global 1000 m/px; detalle 60 m/px solo Luna sur (< -80°) ↔ México
  (lat 14..33, lon -118..-86). No usar el antiguo 500 m/px.
- Dimensiones: terrain, operations, thermal, albedo, ice, soil, aridity. Perfil general por defecto.
- `k` es por destino. Conservar ranking recibido, no ordenar por score.
- `no_data`, pesos opcionales, atributos nulos, patches por destino y warnings
  tienen presentación explícita. No inventar valores faltantes.
- El backend decide el método; el cliente no fuerza hybrid ni RRF.
- Astrobiology se ofrece solo para origen Marte.
- Error en modo API no se sustituye por datos demo.

## Lunar suitability

La UI está preparada para los endpoints propuestos de metadatos/PNG; falta
integración con el backend y artefactos reales. El PNG exportado es una figura
polar, no una textura georreferenciada. Mantener visible:
“Suggestion, not a final site selection: illumination and Earth visibility are not included.”

Arranque, comprobaciones y limitaciones: [README.md](README.md).

## Sincronización

Por instrucción del usuario, antes de editar consultar e integrar origin/main con
`git pull --ff-only origin main`, preservando cambios locales. Si hay divergencia,
resolver la integración sin force-push ni perder trabajo. No confundir fetch con pull.
