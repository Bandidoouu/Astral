# Revisión de entrega ML · 2026-11-14

Alcance acordado con Esteban: cerrar artefactos de ML; no implementar Backend ni
Frontend. Rama `ml/artifact-review`, basada en `ml/gradcam` (#10). No se cambió el
modelo, el entrenamiento, los embeddings ni los rankings; no se repitió la prueba
ciega. No hubo descargas. Windows: 291 GB libres antes de generar; un proceso GPU
a la vez, muestra antes del conjunto completo y ejecución completa en tmux.

## Qué se entrega

Paquete **local** `data/artifacts/release/v2-1km-r3/`: 123 archivos, ~240 MB,
manifest con SHA-256, sin faltantes. Conserva los 49 archivos de r2 y agrega
`gradcam/` con 72 PNG, `index.json` y README. No está subido a GitHub ni transferido
al equipo: los artefactos están fuera de git. El medio de transferencia sigue por
acordar en `docs/contratos.md` (copia por Tailscale o Drive).

Grad-CAM corregido también queda en `data/artifacts/gradcam-r3/`. El directorio
anterior `gradcam/` se conserva como referencia histórica; usar r3 para la entrega.

- 17 sitios × 2 destinos × 3 resultados = 102 asociaciones, **72 pares únicos**.
- Shackleton y de Gerlache comparten un parche; Mons Mouton, Malapert, Haworth,
  Nobile y Faustini comparten otro. Los títulos anteriores se sobrescribían.
  Ahora el PNG identifica IDs y centros; el índice conserva sitios/ranks/distancias.
- Se deriva el coseno de la suma normalizada de cuatro embeddings rotados contra
  el embedding fijo indexado del otro parche. Se desrotan los CAM crudos y se
  promedian antes de normalizar. Diferencia máxima de coseno frente al índice:
  0.000267; máximo por componente del embedding: 0.000716 (tolerancia BF16 0.005).
- Revisión visual: las 72 imágenes en cuatro hojas de contacto y una a resolución
  completa; sin figuras vacías, títulos sobrescritos ni errores de lectura.
- Mapas gruesos y aproximados, normalizados por panel: no son prueba causal ni
  equivalencia geológica. No explican el ranking RRF o el ambiente y no corresponden
  a búsquedas `gravity_scaled` o de 60 m.

Avisos y errores de escala de `ml/search.py` ahora están en inglés. La generación
rechaza reutilizar directorios y el empaquetador rechaza muestras incompletas,
fuentes modificadas y versiones ya existentes.

## Comprobaciones

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python -m unittest discover -s ml/tests -v
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python -m ml.check_delivery \
  --release data/artifacts/release/v2-1km-r3
```

Tres pruebas: gradiente/coseno contrastado con derivada analítica independiente,
asociación compartida de sitios y rechazo de embeddings incompatibles. Verificador:
123 hashes/tamaños, 43 respuestas reales (consultas/rankings/puntajes iguales a la
demo), ambos JSON de aptitud contra contratos, lectura de 72 PNG y errores numéricos.
Avisos comprobados: Marte a 60 m, Luna fuera de cobertura a 60 m e índice ausente.

Texturas de #8 revisadas leyendo `ml/globe-textures` en una copia temporal, sin
cambiar de rama ni escribir en Frontend: 2:1, decodificación de imágenes, rangos en
metros, alfa transparente en aptitud; vista de color, altura, normales y topografía.
Alturas: Tierra −415..6376 m, Luna −9065..10654 m, Marte −8166..21154 m. Los README
ya declaran el relleno visual sin DEM: Antártida a 0 m, extremos polares marcianos
con la fila válida más cercana. Esto no amplía cobertura científica. No se comprobó
el material de Three.js, la orientación al envolver la esfera ni licencias externas
mediante una nueva consulta web. Las leyendas no son mapas 2:1.

## Para compartir con los dueños (pendiente de enviar por Esteban)

**Backend — Angel, Tamara, Ethan:** paquete r3 preparado localmente, mismos índices
y resultados de r2; Grad-CAM corregido bajo los mismos nombres de PNG del contrato.
Cargar la carpeta completa y verificar el manifest. Pendientes de Backend ya
identificados: pasar `scale_mode` a `Searcher.search` y servir los JSON/PNG de aptitud.
No se implementaron aquí.

**Frontend — Hanna y Violeta:** texturas siguen en #8; respuestas y JSON siguen en
#9. Grad-CAM r3 representa parches compartidos, no sitios exactos; limitar su uso a
1 km `same_size`. Pendientes de su integración: `window_km`, criterios marcianos,
texturas y revisión de la etiqueta `PRECOMPUTED` de #9. No se modificó su código.

**Pitch:** usar cifras de evaluación ya guardadas, distinguiendo red sola de RRF,
60 m de 1 km y pruebas de validación de prueba ciega. No afirmar que se validó con
Haughton/McMurdo ni que la invariancia al planeta explica el éxito. El README raíz
y la arquitectura contienen referencias antiguas; este bloque actualiza el README
de ML. La figura de validación de 1 km, UMAP y alturas de detalle quedan para un
bloque posterior; no forman parte de r3.

PR #7–#10 seguían abiertos sin revisiones/comentarios al verificar GitHub. Las
confirmaciones de consumidores y las fusiones siguen pendientes; fusiona una persona.
