# ASTRAL backend

FastAPI service that serves ASTRAL's neural-network results: nearest Earth analogs
for a Moon or Mars site, per-dimension scores and mission-profile weighting.

- API contract: [`../docs/contratos.md`](../docs/contratos.md) (examples in [`../contracts/`](../contracts/))
- Team rules for this module: [`CLAUDE.md`](CLAUDE.md)

```bash
uvicorn app.main:app --reload --port 8000
```
