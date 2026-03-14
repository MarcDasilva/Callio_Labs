"""
ColabFold on Modal — GPU endpoint for protein structure prediction.

Run: modal serve app.py   (ephemeral) or  modal deploy app.py  (persistent)
Then POST sequence(s) to the returned URL to get PDB/JSON model outputs.
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

# --- Images ---

# Official ColabFold image (includes AlphaFold, MMseqs2, kalign, etc.)
# Uses public MSA server by default (no local DB needed).
COLABFOLD_IMAGE = "ghcr.io/sokrypton/colabfold:1.6.0-cuda12"
colabfold_image = modal.Image.from_registry(COLABFOLD_IMAGE)

# Lightweight image for the web endpoint (no GPU).
web_image = modal.Image.debian_slim().pip_install("fastapi[standard]", "httpx")

# --- App ---

app = modal.App("colabfold-genaigenesis", image=web_image)


def _run_colabfold(input_dir: Path, output_dir: Path, num_models: int = 1) -> None:
    """Run colabfold_batch inside the container. Uses public MSA server."""
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    # Optional: reduce memory if needed
    env.setdefault("XLA_PYTHON_CLIENT_MEM_FRACTION", "4.0")
    cmd = [
        "colabfold_batch",
        "--num-models", str(num_models),
        "--num-recycle", "3",
        str(input_dir),
        str(output_dir),
    ]
    subprocess.run(cmd, check=True, env=env, cwd="/app", timeout=1800)


@app.function(
    image=colabfold_image,
    gpu="A100",  # or "T4" for cheaper, "A100" for speed
    timeout=1200,  # 20 min per prediction
    allow_concurrent_inputs=1,
)
def run_prediction(
    fasta_content: str,
    job_name: str = "query",
    num_models: int = 1,
) -> dict[str, Any]:
    """
    Run ColabFold structure prediction on the given FASTA content.
    FASTA can be a single sequence or multiple (for complexes, use : between chains).
    Returns dict with pdb, pdb_b64, json_data, and optional png_b64.
    """
    with tempfile.TemporaryDirectory(prefix="cf_in_") as tmp_in:
        with tempfile.TemporaryDirectory(prefix="cf_out_") as tmp_out:
            input_dir = Path(tmp_in)
            output_dir = Path(tmp_out)

            # Ensure valid FASTA: if no ">" present, wrap as single sequence
            raw = fasta_content.strip()
            if not raw.startswith(">"):
                raw = f">{job_name}\n{raw}"
            (input_dir / "input.fasta").write_text(raw)

            _run_colabfold(input_dir, output_dir, num_models=num_models)

            # ColabFold writes into output_dir; often one subdir per job or flat files
            result_files = list(output_dir.rglob("*.pdb"))
            if not result_files:
                raise FileNotFoundError(
                    f"No PDB produced in {output_dir}; contents: {list(output_dir.rglob('*'))}"
                )
            # Prefer relaxed structure if present
            pdb_path = result_files[0]
            for p in result_files:
                if "relaxed" in p.name.lower() or "rank_001" in p.name:
                    pdb_path = p
                    break

            pdb_content = pdb_path.read_text()

            # Optional: attach JSON (scores, etc.) and PNG if present
            json_path = pdb_path.with_suffix(".json")
            if not json_path.exists():
                json_path = pdb_path.parent / (pdb_path.stem.replace("_relaxed", "") + ".json")
            json_data = None
            if json_path.exists():
                json_data = json.loads(json_path.read_text())

            png_path = pdb_path.with_suffix(".png")
            if not png_path.exists():
                png_path = next(output_dir.rglob("*.png"), None)
            png_b64 = None
            if png_path and png_path.exists():
                png_b64 = base64.b64encode(png_path.read_bytes()).decode()

            return {
                "pdb": pdb_content,
                "pdb_b64": base64.b64encode(pdb_content.encode()).decode(),
                "json": json_data,
                "png_b64": png_b64,
                "job_name": job_name,
            }


@app.function(image=web_image, timeout=900)
@modal.fastapi_endpoint(method="POST")
def predict(body: dict[str, Any]):
    """
    HTTP endpoint: POST JSON with "sequence" (and optional "job_name", "num_models").
    Returns JSON with PDB, base64 PDB, optional scores JSON, and optional PNG as base64.
    """
    sequence = (body.get("sequence") or "").strip()
    if not sequence:
        return {"error": "Missing 'sequence' in request body"}

    job_name = body.get("job_name") or "query"
    num_models = int(body.get("num_models") or 1)
    num_models = max(1, min(5, num_models))

    result = run_prediction.remote(
        fasta_content=sequence,
        job_name=job_name,
        num_models=num_models,
    )
    return result


@app.function(image=web_image, timeout=900)
@modal.fastapi_endpoint(method="GET")
def health():
    """Health check for the service."""
    return {"status": "ok", "service": "colabfold-modal"}


@app.local_entrypoint()
def main():
    """Test run locally: modal run app.py"""
    fasta = ">test\nMKFLNFLLLVALLVVVASSSSGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"
    print("Running ColabFold prediction (this may take several minutes)...")
    out = run_prediction.remote(fasta_content=fasta, job_name="test", num_models=1)
    print("PDB length:", len(out["pdb"]))
    print("Keys:", list(out.keys()))
    if out.get("json"):
        print("JSON keys:", list(out["json"].keys())[:10])
