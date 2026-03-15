"""
ColabFold on Modal — GPU endpoint for protein structure prediction.

Run: modal serve app.py   (ephemeral) or  modal deploy app.py  (persistent)
POST JSON with "sequence" to the predict URL; response is JSON with "pdb", "json", "job_name".
First run can take 3–5 min (model download); later runs ~1–2 min.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import modal

# --- Images & cache ---
# Official ColabFold Docker image (https://github.com/sokrypton/ColabFold)
COLABFOLD_IMAGE = "ghcr.io/sokrypton/colabfold:1.6.0-cuda12"
colabfold_image = modal.Image.from_registry(COLABFOLD_IMAGE)

# Persist model weights so we don't re-download ~3.5GB on every cold start.
# Set COLABFOLD_SKIP_VOLUME=1 to disable (e.g. if jobs hang — volume sync can block).
COLABFOLD_SKIP_VOLUME = os.environ.get("COLABFOLD_SKIP_VOLUME", "").strip() == "1"
colabfold_cache = modal.Volume.from_name("colabfold-cache", create_if_missing=True)
COLABFOLD_CACHE_PATH = "/cache/colabfold"

web_image = modal.Image.debian_slim().pip_install("fastapi[standard]")

# --- App ---

app = modal.App("colabfold-genaigenesis", image=web_image)


def _run_colabfold(input_dir: Path, output_dir: Path, num_models: int = 1) -> None:
    """Run colabfold_batch. Uses public MSA server."""
    import sys
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    env.setdefault("XLA_PYTHON_CLIENT_MEM_FRACTION", "4.0")
    cmd = [
        "colabfold_batch",
        "--num-models", str(num_models),
        "--num-recycle", "3",
        str(input_dir),
        str(output_dir),
    ]
    print(f"[DEBUG] _run_colabfold: cmd={cmd}", flush=True)
    sys.stdout.flush()
    # 15 min max — normal run is 3–5 min (cold) or 1–2 min (warm). Avoid hanging 30 min on a stuck run.
    proc = subprocess.run(
        cmd,
        check=False,
        env=env,
        timeout=900,
        capture_output=True,
        text=True,
    )
    print(f"[DEBUG] _run_colabfold: returncode={proc.returncode}", flush=True)
    if proc.stdout:
        print(f"[DEBUG] _run_colabfold stdout (last 500 chars): {proc.stdout[-500:]}", flush=True)
    if proc.stderr:
        print(f"[DEBUG] _run_colabfold stderr (last 500 chars): {proc.stderr[-500:]}", flush=True)
    sys.stdout.flush()
    if proc.returncode != 0:
        raise RuntimeError(f"colabfold_batch exited with code {proc.returncode}")


@app.function(
    image=colabfold_image,
    gpu="A100",
    timeout=1200,
    volumes={} if COLABFOLD_SKIP_VOLUME else {COLABFOLD_CACHE_PATH: colabfold_cache},
)
@modal.concurrent(max_inputs=1)
def run_prediction(
    fasta_content: str,
    job_name: str = "query",
    num_models: int = 1,
) -> dict[str, Any]:
    """Run ColabFold; returns dict with pdb, json, job_name. Uses official ColabFold image + public MSA server."""
    import sys
    print(f"[DEBUG] run_prediction: start job_name={job_name!r} num_models={num_models} len(sequence)={len(fasta_content)}", flush=True)
    sys.stdout.flush()
    if not COLABFOLD_SKIP_VOLUME:
        colabfold_cache.reload()  # load persisted model weights if present
        print("[DEBUG] run_prediction: cache reloaded", flush=True)
        sys.stdout.flush()
    else:
        print("[DEBUG] run_prediction: volume disabled (COLABFOLD_SKIP_VOLUME=1)", flush=True)
        sys.stdout.flush()
    with tempfile.TemporaryDirectory(prefix="cf_in_") as tmp_in:
        with tempfile.TemporaryDirectory(prefix="cf_out_") as tmp_out:
            input_dir = Path(tmp_in)
            output_dir = Path(tmp_out)

            raw = fasta_content.strip()
            if not raw.startswith(">"):
                raw = f">{job_name}\n{raw}"
            (input_dir / "input.fasta").write_text(raw)
            print("[DEBUG] run_prediction: calling _run_colabfold", flush=True)
            sys.stdout.flush()

            _run_colabfold(input_dir, output_dir, num_models=num_models)

            print("[DEBUG] run_prediction: _run_colabfold returned, scanning for PDBs", flush=True)
            sys.stdout.flush()
            pdbs = list(output_dir.rglob("*.pdb"))
            print(f"[DEBUG] run_prediction: found {len(pdbs)} PDBs: {[str(p.name) for p in pdbs]}", flush=True)
            sys.stdout.flush()
            if not pdbs:
                listing = "\n".join(str(p) for p in output_dir.rglob("*")[:30])
                raise FileNotFoundError(f"No PDB in output dir. Contents:\n{listing}")

            pdb_path = pdbs[0]
            for p in pdbs:
                if "rank_001" in p.name or "relaxed" in p.name.lower():
                    pdb_path = p
                    break
            print(f"[DEBUG] run_prediction: using PDB {pdb_path.name} len={pdb_path.stat().st_size}", flush=True)
            sys.stdout.flush()

            pdb_content = pdb_path.read_text()
            json_data = None
            for cand in (pdb_path.with_suffix(".json"), pdb_path.parent / (pdb_path.stem.replace("_relaxed", "").replace("_unrelaxed", "") + ".json")):
                if cand.exists():
                    json_data = json.loads(cand.read_text())
                    break
            print("[DEBUG] run_prediction: about to commit cache and return", flush=True)
            sys.stdout.flush()
            if not COLABFOLD_SKIP_VOLUME:
                colabfold_cache.commit()  # persist model weights for next run
            print(f"[DEBUG] run_prediction: returning pdb len={len(pdb_content)}", flush=True)
            sys.stdout.flush()
            return {
                "pdb": pdb_content,
                "pdb_b64": base64.b64encode(pdb_content.encode()).decode(),
                "json": json_data,
                "job_name": job_name,
            }


def create_app():
    import fastapi
    web_app = fastapi.FastAPI()

    def _submit(body: dict[str, Any]):
        sequence = (body.get("sequence") or "").strip()
        if not sequence:
            return {"error": "Missing 'sequence' in request body"}
        job_name = body.get("job_name") or "query"
        num_models = max(1, min(5, int(body.get("num_models") or 1)))
        call = run_prediction.spawn(
            fasta_content=sequence,
            job_name=job_name,
            num_models=num_models,
        )
        return {"job_id": call.object_id}

    @web_app.post("/")
    def predict_root(body: dict[str, Any]):
        """Start prediction; returns job_id. Poll GET /result?job_id=<job_id> for result."""
        return _submit(body)

    @web_app.post("/predict")
    def predict_path(body: dict[str, Any]):
        """Same as POST / — use if your client 404s on POST to root."""
        return _submit(body)

    @web_app.get("/result")
    def result(job_id: str):
        """Poll for result. Returns 202 while running, 200 with { pdb, json, job_name } when done, 500 if run failed."""
        import sys
        print(f"[DEBUG] GET /result job_id={job_id[:20]}...", flush=True)
        sys.stdout.flush()
        try:
            function_call = modal.FunctionCall.from_id(job_id)
            out = function_call.get(timeout=0)
            print(f"[DEBUG] GET /result: got result pdb_len={len(out.get('pdb', ''))}", flush=True)
            sys.stdout.flush()
            return {"pdb": out["pdb"], "json": out.get("json"), "job_name": out.get("job_name", "query")}
        except modal.exception.RemoteError as e:
            err_msg = str(e) or "ColabFold run failed"
            print(f"[DEBUG] GET /result: RemoteError type={type(e).__name__} msg={err_msg[:200]}", flush=True)
            sys.stdout.flush()
            return fastapi.responses.JSONResponse(
                {"error": err_msg},
                status_code=500,
            )
        except Exception as e:
            exc_name = type(e).__name__
            exc_msg = str(e)[:200]
            print(f"[DEBUG] GET /result: Exception type={exc_name} msg={exc_msg} (timeout?={'Timeout' in exc_name or 'timeout' in exc_msg.lower()})", flush=True)
            sys.stdout.flush()
            if "Timeout" in exc_name or "timeout" in exc_msg.lower():
                return fastapi.responses.JSONResponse({"status": "pending"}, status_code=202)
            raise

    @web_app.get("/health")
    def health():
        return {"status": "ok", "service": "colabfold-modal"}

    return web_app


@app.function(image=web_image, timeout=900)
@modal.asgi_app()
def web():
    """ASGI app: POST / to submit, GET /result?job_id=... to poll, GET /health. Avoids 150s HTTP limit."""
    return create_app()


@app.local_entrypoint()
def main():
    """Test: modal run app.py"""
    print("Running ColabFold (this may take a few minutes)...")
    out = run_prediction.remote(
        fasta_content="GIVEQCCTSICSLYQLENYCN",
        job_name="test",
        num_models=1,
    )
    print("PDB length:", len(out["pdb"]))
    print("Keys:", list(out.keys()))
