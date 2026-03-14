# ColabFold on Modal

[ColabFold](https://github.com/sokrypton/ColabFold) (AlphaFold2 + MMseqs2) running on [Modal](https://modal.com) GPUs, exposed as an HTTP endpoint you can call to get protein structure predictions.

## Prerequisites

- [Modal account](https://modal.com) and CLI: `pip install modal`
- Log in: `modal token new` (browser auth)

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

You’ll get a temporary URL like `https://<workspace>--predict-dev.modal.run`. Keep the process running while you call the endpoint.

## Deploy (persistent endpoint)

```bash
modal deploy app.py
```

Modal will print the persistent URL for the `predict` and `health` endpoints.

## API

### POST `/predict` (or the deployed URL for `predict`)

Request body (JSON):

| Field       | Type | Required | Description |
|------------|------|----------|-------------|
| `sequence` | str  | Yes      | Protein sequence (one-letter codes) or full FASTA (e.g. `>name\nSEQ`). For complexes, use `:` between chains. |
| `job_name` | str  | No       | Job ID for output (default `"query"`). |
| `num_models` | int | No     | Number of AlphaFold models (1–5, default 1). |

Example:

```bash
curl -X POST https://<your-workspace>--predict.modal.run \
  -H "Content-Type: application/json" \
  -d '{"sequence": "MKFLNFLLLVALLVVVASSSS", "job_name": "my_protein"}'
```

Response (JSON):

- `pdb`: PDB structure as text
- `pdb_b64`: same PDB, base64-encoded
- `json`: ColabFold scores/metadata if available
- `png_b64`: optional confidence plot image (base64)
- `job_name`: echo of job name

### GET `/health`

Returns `{"status": "ok", "service": "colabfold-modal"}`.

## Python client example

```python
import requests

url = "https://<your-workspace>--predict.modal.run"
r = requests.post(
    url,
    json={"sequence": "MKFLNFLLLVALLVVVASSSS", "num_models": 1},
    timeout=600,
)
data = r.json()
if "error" in data:
    print(data["error"])
else:
    pdb_str = data["pdb"]
    with open("prediction.pdb", "w") as f:
        f.write(pdb_str)
```

## Notes

- **MSA**: Predictions use the public ColabFold MSA server (no local DB setup).
- **GPU**: Default is `A100`; change `gpu="T4"` in `app.py` for cheaper, slower runs.
- **Timeouts**: Single predictions typically finish in a few minutes; endpoint and GPU timeouts are set to 15–20 minutes.
- **Complexes**: Use FASTA with `:` between chains, e.g. `>complex\nSEQ1:SEQ2`.

## References

- [ColabFold](https://github.com/sokrypton/ColabFold) — Making protein folding accessible to all
- [Modal](https://modal.com/docs) — Serverless GPU platform
