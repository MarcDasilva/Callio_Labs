"""Request/response schemas for the Primer3 design API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


# Keys that are sequence-specific (passed as seq_args to primer3-py).
PRIMER3_SEQ_KEYS = frozenset({
    "SEQUENCE_ID",
    "SEQUENCE_TEMPLATE",
    "SEQUENCE_TARGET",
    "SEQUENCE_EXCLUDED_REGION",
    "SEQUENCE_INCLUDED_REGION",
    "PRIMER_PRODUCT_SIZE_RANGE",
})

# Keys that are global (passed as global_args). Request may send others.
PRIMER3_GLOBAL_KEYS = frozenset({
    "PRIMER_OPT_SIZE", "PRIMER_MIN_SIZE", "PRIMER_MAX_SIZE",
    "PRIMER_OPT_TM", "PRIMER_MIN_TM", "PRIMER_MAX_TM",
    "PRIMER_MIN_GC", "PRIMER_MAX_GC",
    "PRIMER_PRODUCT_SIZE_RANGE",
    "PRIMER_NUM_RETURN",
})


class DesignTask(BaseModel):
    """One Primer3 design task (one DNA template + target)."""

    SEQUENCE_ID: str
    SEQUENCE_TEMPLATE: str
    SEQUENCE_TARGET: list[int]  # [start, length]
    SEQUENCE_EXCLUDED_REGION: list[list[int]] = Field(default_factory=list)
    PRIMER_PRODUCT_SIZE_RANGE: list[list[int]] | None = None

    model_config = {"extra": "ignore"}


class DesignRequest(BaseModel):
    """POST /design body: up to 3 tasks and optional global_args."""

    tasks: list[DesignTask] = Field(..., min_length=1, max_length=3)
    global_args: dict[str, Any] = Field(default_factory=dict)


class GenomeItem(BaseModel):
    """One genome entry: accession + FASTA sequence (for deriving primer3_tasks)."""

    accession_id: str
    fasta_sequence: str


class AlignmentRequest(BaseModel):
    """POST /design-from-alignment body: full LLM alignment JSON or genomes-only.

    Either:
    - Send primer3_tasks (1–3 tasks) for design, or
    - Send genomes (list of {accession_id, fasta_sequence}); primer3_tasks are
      derived (one task per genome, whole sequence as target).
    Optional: alignment_summary, conserved_regions, variable_regions,
    mutation_hotspots, target_sequences, total_genomes_retrieved, errors.
    """

    alignment_summary: dict[str, Any] | None = None
    conserved_regions: list[dict[str, Any]] | None = None
    variable_regions: list[dict[str, Any]] | None = None
    mutation_hotspots: list[dict[str, Any]] | None = None
    primer3_tasks: list[dict[str, Any]] | None = Field(None, max_length=3)
    genomes: list[GenomeItem] | None = None
    target_sequences: list[str] | None = None
    total_genomes_retrieved: int | None = None
    errors: list[Any] | None = None
    global_args: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}

    @model_validator(mode="after")
    def require_tasks_or_genomes(self) -> "AlignmentRequest":
        if self.primer3_tasks and len(self.primer3_tasks) >= 1:
            return self
        if self.genomes and len(self.genomes) >= 1:
            return self
        # Allow empty: endpoint will return sample data when no real data provided
        return self


class DesignResultItem(BaseModel):
    """One successful task result: sequence_id + full primer3-py result dict."""

    sequence_id: str
    result: dict[str, Any] = Field(description="Full primer3-py design_primers() output (BoulderIO-style)")


class DesignErrorItem(BaseModel):
    """One failed task for the errors array."""

    sequence_id: str
    message: str


class DesignResponse(BaseModel):
    """Response: results for successful tasks, errors for failed ones."""

    results: list[DesignResultItem] = Field(default_factory=list)
    errors: list[DesignErrorItem] = Field(default_factory=list)


# Simplified output: Tm, GC, affinity, and primer sequences for analysis.
class PrimerPairSummary(BaseModel):
    """One primer pair: sequences, Tm, GC, affinity, and product size for analysis."""

    forward_primer: str = Field(description="Forward primer sequence (5' to 3')")
    reverse_primer: str = Field(description="Reverse primer sequence (5' to 3')")
    left_tm: float = Field(description="Forward primer melting temperature (°C)")
    right_tm: float = Field(description="Reverse primer melting temperature (°C)")
    left_gc_percent: float = Field(description="Forward primer GC content (%)")
    right_gc_percent: float = Field(description="Reverse primer GC content (%)")
    affinity_to_target: float = Field(
        description="Affinity to target sequence (0–1); 1 = designed for this target",
    )
    product_size_bp: int = Field(description="Amplicon size (bp) for this pair")


class SimplifiedResultItem(BaseModel):
    """One task: sequence_id and list of primer pairs (Tm, GC, affinity only)."""

    sequence_id: str
    pairs: list[PrimerPairSummary] = Field(default_factory=list)


class SimplifiedDesignResponse(BaseModel):
    """Design response with only Tm, GC content, and affinity to target."""

    results: list[SimplifiedResultItem] = Field(default_factory=list)
    errors: list[DesignErrorItem] = Field(default_factory=list)
