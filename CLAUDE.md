# ASTRAL · NASA Space Apps 2026 · Equipo Dinamita Buena Onda

> **Lee esto completo antes de tocar cualquier cosa.** Este archivo vale para los 6
> integrantes y para cualquier sesión de Claude Code en este repositorio. Cada módulo
> tiene además su propio `CLAUDE.md` con las reglas finas (`ml/`, `backend/`, `frontend/`).

## 1. Qué es ASTRAL (y por qué importa tanto)

**ASTRAL es un "Shazam planetario":** eliges un sitio en la Luna o en Marte y una red
neuronal **propia, entrenada por nosotros** (no una API de LLM) encuentra sus gemelos
en la Tierra.

> **Requisito central:** el usuario hace clic en **cualquier punto** de la Tierra,
> la Luna o Marte y recibe coincidencias en los otros dos. Escala global de
> **1 km/px** (parches de 128 km, los tres cuerpos) y escala de detalle de **60 m/px**
> (solo Luna ↔ Tierra, dentro de su cobertura). Contrato: `docs/contratos.md` §3
> (`target_bodies`, `scale_m`).
>
> **Requisito central: la búsqueda no es solo de forma.** La red se encarga solo del
> terreno; temperatura y albedo se calculan aparte con MODIS, Diviner, LOLA (y TES
> en Marte). Cada dimensión da su puntaje de 0 a 1 por separado y el total se
> pondera por perfil de misión. **Si falta un dato, la dimensión dice "sin dato" y no
> cuenta en el total: nunca se inventan valores.** Además hay una capa de aptitud para
> base lunar con reglas transparentes (pendiente, hielo, temperatura), que es una
> sugerencia: faltan iluminación y visibilidad de la Tierra. Para cada gemelo dice **en qué se parece** (relieve, operaciones,
temperatura, materiales) y **en qué no** (gravedad, vacío, radiación). Todo se ve en un
"mapa astral" 3D de los tres cuerpos.

- **Reto oficial de la NASA:** *"Identify Earth Locations that Analog the Permanent
  Moon Base Locations and Mars"*. Hay que identificar y caracterizar análogos
  terrestres **nuevos** de futuras bases o sitios de aterrizaje, explicar qué es
  análogo y qué no, y presentarlo como mapa, visualización o herramienta.
- **El momento de la demo:** la red redescubre **sola** El Pinacate (Sonora), donde la
  NASA entrenó a los astronautas del Apolo de 1965 a 1970, **sin haberlo visto en el
  entrenamiento**, y luego propone sitios nuevos en México.
- **Lo que el jurado califica:** Impact, Creativity, Validity, Relevance,
  Presentation. Ganamos si demostramos que **la red le gana a una fórmula sencilla**,
  que **se explica**, y que **reconocemos con honestidad los límites** de la Tierra
  como análogo.
- **Formato:** 24 horas. MVP funcionando en **H16**, entrega en **H23**.

Cada decisión de código, de diseño o de pitch se mide contra una pregunta:
**¿esto ayuda a que el jurado vea que la red encuentra análogos reales y lo explica?**
Si no, no es prioridad.

## 2. Equipo y dueños de cada módulo

| Módulo | Carpeta | Integrantes | Dueño de |
| --- | --- | --- | --- |
| **Red neuronal (el corazón)** | `ml/` | Esteban (con Claude Code) | Parches, modelo, embeddings, índice, validación, **contratos** |
| Frontend 3D | `frontend/` | Hanna | Globos, capas, arcos, galaxia (React Three Fiber) |
| Frontend UI | `frontend/` | Gris | Tarjetas, radar, perfiles de misión, idioma |
| Backend | `backend/` | Angel, Tamara, Ethan | API FastAPI, búsqueda, puntajes, datos auxiliares |

- **ML es el corazón del proyecto**: el resto consume lo que la red produce. Por eso
  el equipo de ML **también puede modificar el backend** (siempre avisando, ver §4).
- Los **contratos** entre módulos (`contracts/` y `docs/contratos.md`) los define ML
  junto con quien los consume.

## 3. Mapa del repositorio

```text
Astral/
├── CLAUDE.md              ← este archivo (reglas de todo el equipo)
├── README.md              ← presentación del proyecto (en inglés, lo ven los jueces)
├── CONTRIBUTING.md        ← cómo trabajar: ramas, commits, PRs, avisos
├── docs/
│   ├── arquitectura.md    ← cómo fluye todo: datos → red → API → 3D
│   ├── datos.md           ← fuentes oficiales, procedencia y comandos de descarga
│   └── contratos.md       ← FUENTE DE VERDAD de los formatos entre módulos
├── contracts/             ← ejemplos JSON reales de cada contrato (para mocks y pruebas)
├── ml/                    ← red neuronal (ver ml/CLAUDE.md)
├── backend/               ← API FastAPI (ver backend/CLAUDE.md)
├── frontend/              ← React Three Fiber (ver frontend/CLAUDE.md)
├── data/                  ← datos y artefactos, FUERA de git (pesan GB)
├── .githooks/             ← hook que bloquea co-autores de IA
└── .github/               ← plantilla de PR y verificación automática
```

## 4. Reglas de oro (para personas y para Claude Code)

### 4.1 Si un cambio afecta lo que trabaja otro integrante, se avisa SIEMPRE

Un cambio "afecta a otro" si toca un **contrato** (`contracts/`, `docs/contratos.md`),
un **artefacto** que otro consume (`data/artifacts/*`), o **código de un módulo ajeno**.

Protocolo obligatorio:

1. **Claude hace el cambio en una rama** (`ml/...`, `backend/...`, `frontend/...`),
   **hace commit y push**, y abre un PR (o, si no hay PR, comparte el link de la rama).
2. En la descripción del PR escribe **qué cambia para el integrante afectado** y qué
   tiene que hacer (con un ejemplo antes/después si es un formato).
3. Se **avisa al integrante dueño** del módulo afectado (por el chat del equipo).
4. **El integrante prueba y nos dice** si funciona o qué le falta. **No se fusiona a
   `main` un cambio de contrato sin esa confirmación.**
5. Se actualiza `docs/contratos.md` y el ejemplo en `contracts/` **en el mismo PR**.

Esto aplica en las dos direcciones: si backend o frontend necesitan que cambie algo
de ML, siguen el mismo protocolo y nos avisan a nosotros.

### 4.2 Ninguna inteligencia artificial aparece como autor o co-autor

- **Prohibido** agregar `Co-Authored-By: Claude`, `Copilot`, `ChatGPT`, `Gemini` o
  cualquier IA en commits o PRs, y cualquier línea tipo "Generated with ...".
- Los commits salen **solo** con el nombre del integrante que los hace.
- Esto lo hacen cumplir: `.claude/settings.json` (Claude Code no agrega la línea),
  el hook `.githooks/commit-msg` (rechaza el commit) y la verificación de GitHub en
  cada PR. **Cada integrante debe activar el hook** (ver `CONTRIBUTING.md`).
- El uso de IA sí se **declara en la página de envío** del hackathon, como piden las
  reglas; lo que no se hace es ponerla como contribuidor.

### 4.3 Datos de las fuentes oficiales del reto (obligatorio usarlas)

**Fuente de verdad: `docs/datos.md`** (lista oficial con enlaces, procedencia de cada
archivo, comandos de descarga y pendientes). Resumen:

- NASA: **Earthdata Search, Worldview, PDS, LRO y LRO Diviner**. Agencias asociadas:
  ESA (Copernicus Data Space, Open Science Catalog), JAXA (G-Portal), CSA (RADARSAT).
- No estamos limitados a esa lista. **Lo único obligatorio es usar datos de la NASA,
  y ya se cumple.** Diviner y las agencias asociadas son opcionales; ya usamos datos
  de JAXA a través de SLDEM2015 (LOLA + Kaguya).
- Aplica también al frontend: texturas de los globos e imágenes de los análogos
  salen de Worldview/GIBS, LRO y PDS.
- Toda fuente fuera de la lista (p. ej. Natural Earth para nombres de estados) se
  justifica y se cita. **Antes de bajar algo nuevo, se registra en `docs/datos.md`.**

### 4.4 Lo que ve el jurado va en inglés

README, gráficas, etiquetas, la interfaz y el video. La documentación interna
(`CLAUDE.md`, `docs/`, `CONTRIBUTING.md`) va en español.

### 4.5 Otras reglas

- **Que funcione de punta a punta antes que bonito.** Nada de refactors grandes
  después de H16. Después de H20 solo se arreglan errores.
- **Commits pequeños y frecuentes**, mensajes claros en inglés.
- **Nunca subir datos ni modelos a git** (`data/` está ignorada). Los artefactos se
  comparten por la ruta acordada en `docs/contratos.md`.
- **No hacer `push --force` a `main`.** No reescribir historia compartida.
- Si una decisión cambia algo de un `CLAUDE.md` o de `docs/`, **se actualiza en el
  mismo commit**.

### 4.6 Git en el equipo (vigente desde H7)

- **Nunca trabajar directo en `main` ni en ramas ajenas.** ML trabaja en ramas `ml/...`.
- **Hacer commit antes de cambiar de rama.** Antes de un `merge`, revisar que no queden
  marcas de conflicto (`git grep -n -E "^(<<<<<<<|>>>>>>>)"`).
- Claude abre los PR de sus ramas con `gh` (instalado en `~/.local/bin/gh`); **las
  fusiones a `main` las hace una persona después de revisarlas.**
- Al empezar a trabajar: `git pull` de `main` y verificar que todo corra.

## 5. Checkpoints del equipo

**Estado del frente de ML (H7):** v2 a 60 m en producción (prueba ciega: la red deja El
Pinacate en el lugar 147 de 55,444 contra 320 de la fórmula); v3 multimodal probado y
descartado por validación. Por recomendación de un mentor, los resultados hacia la
Tierra salen solo de zonas prometedoras (MODIS MCD12C1: desiertos, matorral disperso,
pastizal, hielo; ~49% de los parches) y la búsqueda tendrá `scale_mode`
(`same_size` / `gravity_scaled`). Escala de 1 km lista (red propia de 3 cuerpos:
Olympus Mons → Mauna Loa en el lugar 1 de 7,669; Pinacate ciego en 0.48%), con
`gravity_scaled` y capa de aptitud de Marte (MOLA + Mars Odyssey). Paquete `release/v2-1km`. Detalle completo:
`ml/CLAUDE.md` §1b.


| Hora | Qué debe estar listo |
| --- | --- |
| H3 | Parches de la Luna y México |
| H8 | Entrenamiento corriendo; backend responde con datos de ejemplo (`contracts/`); frontend muestra los globos |
| H12 | **Búsqueda de punta a punta**: el frontend pide, el backend busca en el índice real |
| H16 | **MVP** completo |
| H20 | Congelamiento: solo errores |
| H23 | Envío |
