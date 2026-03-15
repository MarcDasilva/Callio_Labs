"""Run primer design for each task; return full results and log errors.

Uses a simple pure-Python designer (no Primer3) to avoid timeouts.
"""

from __future__ import annotations

import logging
from typing import Any

from .schemas import (
    AlignmentRequest,
    DesignErrorItem,
    DesignRequest,
    DesignResultItem,
    DesignResponse,
    DesignTask,
    GenomeItem,
    PrimerPairSummary,
    SimplifiedDesignResponse,
    SimplifiedResultItem,
)


def get_sample_design_response() -> SimplifiedDesignResponse:
    """Return sample primer results matching real response shape (for empty/invalid requests)."""
    return SimplifiedDesignResponse(
        results=[
            SimplifiedResultItem(
                sequence_id="SAMPLE_REF",
                pairs=[
                    PrimerPairSummary(
                        forward_primer="ATGCGATCGAGCTAGCTACGA",
                        reverse_primer="TCGTAGCTAGCTCGATCGCAT",
                        left_tm=59.2,
                        right_tm=58.8,
                        left_gc_percent=50.0,
                        right_gc_percent=47.6,
                        affinity_to_target=1.0,
                        product_size_bp=185,
                    ),
                    PrimerPairSummary(
                        forward_primer="GCTACGTACGATCGATCGATC",
                        reverse_primer="GATCGATCGATCGTACGTAGC",
                        left_tm=60.1,
                        right_tm=59.5,
                        left_gc_percent=52.4,
                        right_gc_percent=52.4,
                        affinity_to_target=1.0,
                        product_size_bp=212,
                    ),
                    PrimerPairSummary(
                        forward_primer="CAGCTAGCTACGATCGATCTA",
                        reverse_primer="TAGATCGATCGTAGCTAGCTG",
                        left_tm=57.8,
                        right_tm=60.3,
                        left_gc_percent=45.0,
                        right_gc_percent=50.0,
                        affinity_to_target=1.0,
                        product_size_bp=198,
                    ),
                ],
            ),
        ],
        errors=[],
    )
from .simple_primer_design import design_primers as simple_design_primers


def _to_json_safe(obj: Any) -> Any:
    """Convert dict/list/tuple to JSON-serializable form (tuples -> lists)."""
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(x) for x in obj]
    return obj

logger = logging.getLogger(__name__)

# Default global args: looser for demo; wider than strict defaults but not extreme (keeps runtime reasonable).
DEFAULT_GLOBAL_ARGS: dict[str, Any] = {
    "PRIMER_NUM_RETURN": 3,
    "PRIMER_PRODUCT_SIZE_RANGE": [[80, 600]],
    "PRIMER_OPT_SIZE": 22,
    "PRIMER_MIN_SIZE": 14,
    "PRIMER_MAX_SIZE": 32,
    "PRIMER_OPT_TM": 60.0,
    "PRIMER_MIN_TM": 48.0,
    "PRIMER_MAX_TM": 72.0,
    "PRIMER_MIN_GC": 20.0,
    "PRIMER_MAX_GC": 85.0,
}


def _build_global_args(global_args: dict[str, Any]) -> dict[str, Any]:
    """Merge request global_args with defaults; ensure PRIMER_NUM_RETURN=3."""
    merged = {**DEFAULT_GLOBAL_ARGS, **global_args}
    merged["PRIMER_NUM_RETURN"] = 3
    return merged


def _run_simple_design(task_dict: dict[str, Any], global_args: dict[str, Any]) -> dict[str, Any]:
    """Call simple Python primer designer; return Boulder-style result dict."""
    seq = task_dict["SEQUENCE_TEMPLATE"]
    seq_id = task_dict["SEQUENCE_ID"]
    target = task_dict.get("SEQUENCE_TARGET") or [0, 80]
    if isinstance(target, (list, tuple)) and len(target) >= 2:
        target_start, target_len = int(target[0]), int(target[1])
    else:
        target_start, target_len = 0, 80
    product_range = (
        task_dict.get("PRIMER_PRODUCT_SIZE_RANGE")
        or global_args.get("PRIMER_PRODUCT_SIZE_RANGE")
        or [[80, 400]]
    )
    if product_range and isinstance(product_range[0], (list, tuple)):
        product_min, product_max = int(product_range[0][0]), int(product_range[0][1])
    else:
        product_min, product_max = 80, 400
    num_return = int(global_args.get("PRIMER_NUM_RETURN", 3))
    return simple_design_primers(
        sequence=seq,
        sequence_id=seq_id,
        target_start=target_start,
        target_len=target_len,
        product_min=product_min,
        product_max=product_max,
        num_return=num_return,
    )


def run_design(request: DesignRequest) -> DesignResponse:
    """
    Run simple primer design for each task. Return all successful results; log and collect
    errors for failed tasks (partial success). No Primer3 dependency.
    """
    results: list[DesignResultItem] = []
    errors: list[DesignErrorItem] = []
    global_args = _build_global_args(request.global_args)

    for task in request.tasks:
        task_dict = task.model_dump()
        seq_id = task_dict["SEQUENCE_ID"]
        try:
            raw = _run_simple_design(task_dict, global_args)
            results.append(DesignResultItem(sequence_id=seq_id, result=_to_json_safe(raw)))
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            logger.exception("Primer design failed for sequence_id=%s: %s", seq_id, msg)
            errors.append(DesignErrorItem(sequence_id=seq_id, message=msg))

    return DesignResponse(results=results, errors=errors)


def to_simplified_response(full: DesignResponse) -> SimplifiedDesignResponse:
    """Reduce full design result to sequences, Tm, GC, affinity, and product size."""
    simplified_results: list[SimplifiedResultItem] = []
    for item in full.results:
        pairs: list[PrimerPairSummary] = []
        raw = item.result
        n = raw.get("PRIMER_PAIR_NUM_RETURNED", 0) or 0
        for i in range(n):
            forward = raw.get(f"PRIMER_LEFT_{i}_SEQUENCE", "") or ""
            reverse = raw.get(f"PRIMER_RIGHT_{i}_SEQUENCE", "") or ""
            left_tm = raw.get(f"PRIMER_LEFT_{i}_TM", 0.0)
            right_tm = raw.get(f"PRIMER_RIGHT_{i}_TM", 0.0)
            left_gc = raw.get(f"PRIMER_LEFT_{i}_GC_PERCENT", 0.0)
            right_gc = raw.get(f"PRIMER_RIGHT_{i}_GC_PERCENT", 0.0)
            product_size = raw.get(f"PRIMER_PAIR_{i}_PRODUCT_SIZE", 0) or 0
            affinity = 1.0
            pairs.append(
                PrimerPairSummary(
                    forward_primer=forward,
                    reverse_primer=reverse,
                    left_tm=float(left_tm),
                    right_tm=float(right_tm),
                    left_gc_percent=float(left_gc),
                    right_gc_percent=float(right_gc),
                    affinity_to_target=affinity,
                    product_size_bp=int(product_size),
                )
            )
        simplified_results.append(SimplifiedResultItem(sequence_id=item.sequence_id, pairs=pairs))
    return SimplifiedDesignResponse(results=simplified_results, errors=full.errors)


# Small target (bp) when deriving from genomes so "span target" is easy to satisfy.
_DEFAULT_TARGET_LEN = 80
# Product size for genome-derived: min must cover target, max loose so pairs exist.
_DEFAULT_PRODUCT_MIN = 80
_DEFAULT_PRODUCT_MAX = 600


def _genomes_to_primer3_tasks(genomes: list[GenomeItem]) -> list[dict[str, Any]]:
    """Build primer3_tasks from genomes: one task per genome.
    Uses a small 5' target (80 bp) so Primer3 can find pairs that span it with product 80-600.
    Uses at most the first 3 genomes to match the design task limit.
    """
    tasks: list[dict[str, Any]] = []
    for g in genomes[:3]:
        seq = g.fasta_sequence
        target_len = min(_DEFAULT_TARGET_LEN, len(seq))
        tasks.append({
            "SEQUENCE_ID": g.accession_id,
            "SEQUENCE_TEMPLATE": seq,
            "SEQUENCE_TARGET": [0, target_len],
            "PRIMER_PRODUCT_SIZE_RANGE": [[_DEFAULT_PRODUCT_MIN, _DEFAULT_PRODUCT_MAX]],
        })
    return tasks


def run_design_from_alignment(request: AlignmentRequest) -> DesignResponse:
    """Extract or derive primer3_tasks from the request and run design."""
    raw_tasks: list[dict[str, Any]]
    global_args_override = dict(request.global_args)
    if request.primer3_tasks:
        raw_tasks = request.primer3_tasks
    elif request.genomes:
        raw_tasks = _genomes_to_primer3_tasks(request.genomes)
        # Force product size so design finds pairs (small target + 80-600 bp product).
        global_args_override["PRIMER_PRODUCT_SIZE_RANGE"] = [[_DEFAULT_PRODUCT_MIN, _DEFAULT_PRODUCT_MAX]]
    else:
        raw_tasks = []

    tasks: list[DesignTask] = []
    for raw_task in raw_tasks:
        # DesignTask ignores extra keys (region_type, conservation_score, etc.)
        tasks.append(DesignTask.model_validate(raw_task))

    design_request = DesignRequest(tasks=tasks, global_args=global_args_override)
    return run_design(design_request)
