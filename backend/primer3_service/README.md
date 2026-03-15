# Primer3 Design Service

FastAPI service that wraps primer3-py: accepts up to 3 DNA sequences, returns 3 primer pairs per sequence (9 total) with full statistics (Tm, GC%, length, product size, penalty, etc.).

## Run

From the repo root or from `backend`:

```bash
cd backend
uvicorn primer3_service.main:app --reload --port 8001
```

- **GET /health** — liveness
- **POST /design** — body: `{ "tasks": [ { "SEQUENCE_ID", "SEQUENCE_TEMPLATE", "SEQUENCE_TARGET", ... } ], "global_args": {} }`

See the plan at `.cursor/plans/primer3_server_workflow_*.plan.md` for full request/response schema.
