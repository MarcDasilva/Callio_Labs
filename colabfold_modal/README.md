# ColabFold on Modal

[ColabFold](https://github.com/sokrypton/ColabFold) (AlphaFold2 + MMseqs2) running on [Modal](https://modal.com) GPUs, exposed as an HTTP endpoint you can call to get protein structure predictions.

## Architecture (what runs where)

Modal **does not** run the whole genaigenesis repo. It runs only this ColabFold service:

| Part | Where it runs | Containerization |
|------|----------------|------------------|
| **Frontend** (Next.js) | Your machine or Vercel | Not on Modal |
| **Next.js API routes** (`/api/colabfold/*`) | Your machine or Vercel | Not on Modal |
| **ColabFold web API** (POST /, GET /result) | Modal | Modal image: `debian_slim` + FastAPI |
| **ColabFold GPU job** (`run_prediction`) | Modal | **Official ColabFold Docker image** `ghcr.io/sokrypton/colabfold:1.6.0-cuda12` |

So: the heavy GPU work is already containerized with the official image. The rest of the repo (frontend, backend) stays off Modal. No need to containerize the entire repo into one image.

## ColabFold (official) setup

This app follows the [official ColabFold repo](https://github.com/sokrypton/ColabFold) setup:

- **Image**: Official Docker image `ghcr.io/sokrypton/colabfold:1.6.0-cuda12` (see [Installation](https://github.com/sokrypton/ColabFold#installation)).
- **MSA**: Uses the **public MSA server** (no local database). Queries are serial from a single IP; do not use multiple machines to hit the server (see [FAQ](https://github.com/sokrypton/ColabFold#is-it-okay-to-use-the-mmseqs2-msa-server-on-a-local-computer)).
- **Batch**: Runs `colabfold_batch` with `--num-models` and `--num-recycle 3`. First run downloads ~3.5GB of weights to `/cache/colabfold`; we persist that with a Modal Volume so later runs skip the download.

## Prerequisites

- [Modal account](https://modal.com) and CLI: `pip install modal`
- Log in: `modal token new` (browser auth)

## What to run (step by step)

Use **two terminals**.

**Terminal 1 — Modal (ColabFold backend)**  
From repo root:

```bash
cd colabfold_modal
modal serve app.py
```

To disable the cache volume (if jobs hang and you suspect volume sync):  
`COLABFOLD_SKIP_VOLUME=1 modal serve app.py`. First run will re-download ~3.5GB.

Leave the server running. Note the **web** URL, e.g. `https://YOUR_WORKSPACE--colabfold-genaigenesis-web-dev.modal.run`.

**Terminal 2 — Next.js (frontend + API)**  
From repo root:

```bash
cd frontend
npm run dev
```

In `frontend/.env.local` set (no trailing slash):

```
NEXT_PUBLIC_COLABFOLD_PREDICT_URL=https://YOUR_WORKSPACE--colabfold-genaigenesis-web-dev.modal.run
```

Restart the Next.js dev server after changing `.env.local`. Then open http://localhost:3000, go to the dashboard, and click **Predict structure**.

**If it runs >10 min:** The UI will stop and ask you to check the Modal terminal. In the terminal where `modal serve` is running, look for:
- `[DEBUG] run_prediction: start` — confirms the GPU job started (may appear only when the GPU container runs).
- `[DEBUG] _run_colabfold: returncode=...` — if you never see this, `colabfold_batch` is stuck (e.g. download or MSA).
- `GET /result -> 500` and `RemoteError` — the GPU run failed; the traceback or stderr snippet above it is the cause.
- If you only ever see `GET /result -> 202` and no `run_prediction` logs, try **disabling the volume** in case `volume.reload()` is blocking: stop the server, then run `COLABFOLD_SKIP_VOLUME=1 modal serve app.py` and try Predict again.
- Otherwise stop with Ctrl+C, fix any env/network issue, then run `modal serve app.py` again and try Predict again.

**Debug:** With debug logging enabled you’ll see:
- **Modal terminal**: `[DEBUG]` lines for colabfold_batch, PDB discovery, GET /result (pending vs success vs RemoteError).
- **Next.js terminal**: `[DEBUG predict]` and `[DEBUG result]` for submit URL, job_id, and each poll.
- **Browser console** (F12 → Console): `[DEBUG ColabFold]` for submit, poll count, and final status. The UI shows “Waiting for result…” while polling.

## Run locally (test)

From this directory:

```bash
cd colabfold_modal
modal run app.py
```

This runs a single prediction via `run_prediction` (no HTTP). Use this to confirm the ColabFold image and GPU work.

## Serve (ephemeral URL)

```bash
modal serve app.py
```

You’ll get a `web => ...` URL (one base URL for the app). Keep the process running and set it in the frontend `.env.local` (see below).

## Deploy (persistent endpoint)

```bash
modal deploy app.py
```

Modal will print the persistent URL for the `web` endpoint.

## API (spawn + poll — avoids 150s HTTP limit)

### POST `/`

Starts a prediction and returns immediately with a job ID. Does not wait for the run to finish.

Request body (JSON):

| Field       | Type | Required | Description |
|------------|------|----------|-------------|
| `sequence` | str  | Yes      | Protein sequence (one-letter codes) or full FASTA (e.g. `>name\nSEQ`). For complexes, use `:` between chains. |
| `job_name` | str  | No       | Job ID for output (default `"query"`). |
| `num_models` | int | No     | Number of AlphaFold models (1–5, default 1). |

Response (JSON): `{ "job_id": "<call_id>" }`.

### GET `/result?job_id=<job_id>`

Polls for the result of a job started with POST `/`. Returns **202** with `{ "status": "pending" }` while the run is in progress; **200** with `{ "pdb": "...", "json": {...}, "job_name": "..." }` when done.

## Python client example

```python
import time
import requests

base = "https://<your-workspace>--colabfold-genaigenesis-web.modal.run"
r = requests.post(
    base,
    json={"sequence": "MKFLNFLLLVALLVVVASSSS", "num_models": 1},
    timeout=30,
)
data = r.json()
if "error" in data:
    print(data["error"])
    exit(1)
job_id = data["job_id"]
while True:
    r2 = requests.get(f"{base}/result", params={"job_id": job_id}, timeout=120)
    if r2.status_code == 200:
        pdb_str = r2.json()["pdb"]
        with open("prediction.pdb", "w") as f:
            f.write(pdb_str)
        break
    if r2.status_code != 202:
        print(r2.status_code, r2.text)
        break
    time.sleep(5)
```

## Frontend 3D viewer

The repo’s Next.js frontend can show predicted structures in a 3D viewer. Set the ColabFold base URL in `frontend/.env.local` (from `modal serve` output — use the **web** URL, no trailing slash):

```bash
NEXT_PUBLIC_COLABFOLD_PREDICT_URL=https://<workspace>--colabfold-genaigenesis-web-dev.modal.run
```

The frontend will POST to this URL and poll `.../result?job_id=...` until the prediction is ready.

Use the “Protein structure (ColabFold)” section on the dashboard: enter a sequence, click **Predict structure**, then view the 3D model (optionally colored by pLDDT confidence).

## Notes

- **MSA**: Uses the public ColabFold MSA server (no local DB). Keep queries serial from one IP.
- **Cache**: Model weights are stored in a Modal Volume (`colabfold-cache`); first run downloads once, then reuse.
- **GPU**: Default is `A100`; change `gpu="T4"` in `app.py` for cheaper, slower runs.
- **Timeouts**: Single predictions typically finish in a few minutes; endpoint and GPU timeouts are set to 15–20 minutes.
- **Complexes**: Use FASTA with `:` between chains, e.g. `>complex\nSEQ1:SEQ2`.

## References

- [ColabFold](https://github.com/sokrypton/ColabFold) — Making protein folding accessible to all
- [Modal](https://modal.com/docs) — Serverless GPU platform
