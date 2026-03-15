"""FastAPI app for the Primer3 design service (POST /design, GET /health)."""
# To run the server: uvicorn primer3_service.main:app --reload --port 8001

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from .design import (
    get_sample_design_response,
    run_design,
    run_design_from_alignment,
    to_simplified_response,
)
from .schemas import AlignmentRequest, DesignRequest, DesignResponse, SimplifiedDesignResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Primer3 Design Service",
    version="0.1.0",
    description="Accepts up to 3 DNA sequences, returns 3 primer pairs per sequence (9 total) with full primer3-py statistics.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


@app.post("/design", response_model=SimplifiedDesignResponse)
async def design(request: DesignRequest) -> SimplifiedDesignResponse:
    """
    Run primer design on up to 3 tasks. Returns only Tm, GC content, and
    affinity to target per primer pair; errors for failed tasks.
    """
    logger.info("POST /design: %d task(s)", len(request.tasks))
    if not request.tasks:
        raise HTTPException(status_code=400, detail="tasks must contain at least one task")
    if len(request.tasks) > 3:
        raise HTTPException(status_code=400, detail="At most 3 tasks allowed")
    full = run_design(request)
    return to_simplified_response(full)


def _has_real_data(request: AlignmentRequest) -> bool:
    """True if request has primer3_tasks or genomes with at least one valid item."""
    if request.primer3_tasks and len(request.primer3_tasks) > 0:
        return True
    if request.genomes and len(request.genomes) > 0:
        # Check for at least one genome with non-empty sequence
        for g in request.genomes:
            if g.fasta_sequence and len(g.fasta_sequence.strip()) >= 50:
                return True
        return False
    return False


@app.post("/design-from-alignment", response_model=SimplifiedDesignResponse)
async def design_from_alignment(request: AlignmentRequest) -> SimplifiedDesignResponse:
    """
    Accept alignment JSON (or genomes). Returns primer pairs with sequences,
    Tm, GC, affinity, and product size. If no real data is provided, returns
    sample data in the same shape for testing/demos.
    """
    if not _has_real_data(request):
        logger.info("POST /design-from-alignment: no real data, returning sample response")
        return get_sample_design_response()
    n_tasks = len(request.primer3_tasks) if request.primer3_tasks else (len(request.genomes) if request.genomes else 0)
    logger.info("POST /design-from-alignment: %d task(s) (primer3_tasks=%s, genomes=%s)",
                n_tasks, bool(request.primer3_tasks), bool(request.genomes))
    full = run_design_from_alignment(request)
    return to_simplified_response(full)
