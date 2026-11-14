# Cómo trabajamos en ASTRAL

Lee primero el `CLAUDE.md` de la raíz: ahí está qué es el proyecto y las reglas de oro.

## 1. Primer día (cada integrante, una sola vez)

```bash
git clone https://github.com/Bandidoouu/Astral.git
cd Astral
git config core.hooksPath .githooks     # OBLIGATORIO: bloquea co-autores de IA
```

Revisa que tus commits salgan con **tu** nombre y correo de GitHub:

```bash
git config user.name      # tu nombre
git config user.email     # el correo de tu cuenta de GitHub
```

Si usas Claude Code, el archivo `.claude/settings.json` ya le impide agregar la línea
de co-autor. Si usas otra herramienta (Copilot, Cursor, etc.), desactiva la opción
de "co-author" o "attribution" que tenga.

## 2. Ramas

- `main` siempre debe funcionar. **Nadie hace push directo a `main` con cambios
  que afecten a otro módulo**, y nadie hace `push --force` a `main`.
- Una rama por tarea, con el módulo como prefijo:
  - `ml/embeddings-faiss`, `ml/fix-holdout`
  - `backend/similar-endpoint`, `backend/thermal-scores`
  - `frontend/globe-arcs`, `frontend/radar-card`
  - `docs/contratos-galaxy` (cambios de contrato)
- Cambios pequeños **dentro de tu propio módulo** que no afectan a nadie pueden ir
  directo a `main` si el equipo así lo decide durante el hackathon; ante la duda, PR.

## 3. Commits

- Pequeños y frecuentes. Mensaje en inglés, en imperativo:
  `Add FAISS index builder`, `Fix lon wraparound in moon patches`.
- **Sin `Co-Authored-By` de ninguna IA ni "Generated with ..."**. El hook los rechaza
  y la verificación de GitHub marca el PR en rojo.
- Nunca subir `data/`, modelos (`*.pt`), índices (`*.faiss`), `.venv/` ni
  `node_modules/`.

## 4. Pull requests

Usa la plantilla (`.github/pull_request_template.md`). Lo más importante es la
sección **"¿Afecta a otro módulo?"**.

## 5. Protocolo cuando un cambio afecta a otro integrante

Aplica cuando tocas un contrato (`contracts/`, `docs/contratos.md`), un artefacto que
otro consume, o código de un módulo que no es tuyo.

1. Haz el cambio en una rama, **commit y push** (si lo hace Claude Code, Claude hace
   el push).
2. Abre un PR y explica **qué cambia para el otro integrante** y qué tiene que hacer,
   con un ejemplo antes/después.
3. **Avisa al integrante** por el chat del equipo con el link del PR.
4. **El integrante prueba y nos responde** (aprueba el PR o dice qué falta).
5. Solo entonces se fusiona a `main`. En el mismo PR se actualizan
   `docs/contratos.md` (incluida su tabla de historial) y el ejemplo de `contracts/`.

| Si cambias... | Avisa a |
| --- | --- |
| `docs/contratos.md` §1-2 (artefactos, metadatos) | Backend (Angel, Tamara, Ethan) |
| `docs/contratos.md` §3-5 (API) | Frontend (Hanna, Gris) y Backend |
| `galaxy.json`, alturas de detalle | Hanna |
| Puntajes, perfiles, textos de la tarjeta | Gris |
| Código en `backend/` (siendo de ML) | Backend |
| Algo que la red necesita del backend | ML (Esteban) |

## 6. Idioma

- Interno (este archivo, `CLAUDE.md`, `docs/`): español.
- Lo que ve el jurado (README, interfaz, gráficas, video): **inglés**.
