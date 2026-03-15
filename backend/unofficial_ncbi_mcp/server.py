"""FastMCP server: tools and resources for NCBI Datasets API."""

from __future__ import annotations

import json
import os
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .client import NCBIClient, NCBIError

mcp = FastMCP(
    name="ncbi-datasets",
    version="2.0.0",
)


# ----- HTTP-only routes (no MCP/SSE) -----
# Use these for health checks; /mcp requires Accept: text/event-stream for MCP clients.


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    """Health check. Safe to curl without Accept: text/event-stream."""
    return JSONResponse({"status": "healthy", "service": "ncbi-datasets-mcp", "version": "2.0.0"})


@mcp.custom_route("/", methods=["GET"])
async def root(_request: Request) -> JSONResponse:
    """Root info. MCP endpoint is at /mcp (requires Accept: text/event-stream)."""
    return JSONResponse({
        "service": "ncbi-datasets-mcp",
        "version": "2.0.0",
        "mcp_endpoint": "/mcp",
        "mcp_note": "MCP clients must send Accept: text/event-stream when connecting to /mcp",
        "health": "/health",
    })


def _client() -> NCBIClient:
    return NCBIClient()


def _json_text(obj: Any) -> str:
    return json.dumps(obj, indent=2)


MAX_GENE_CHARS = 8000


def _truncate_gene_output(text: str) -> str:
    """Hard-cap any gene-related output to MAX_GENE_CHARS to protect the context window."""
    if len(text) <= MAX_GENE_CHARS:
        return text
    notice = json.dumps({
        "truncation_warning": (
            f"Response was {len(text)} chars and has been truncated to "
            f"{MAX_GENE_CHARS} chars. Use more specific queries or filters "
            "to reduce the response size."
        ),
    })
    budget = MAX_GENE_CHARS - len(notice) - 5
    return text[:max(budget, 200)] + "\n..." + notice


# ----- Resources -----


@mcp.resource("ncbi://genome/{accession}")
def resource_genome(accession: str) -> str:
    """Complete genome assembly information including statistics and annotation."""
    try:
        data = _client().genome_by_accession(accession)
        return _json_text(data)
    except NCBIError as e:
        return _json_text({"error": str(e), "accession": accession})


@mcp.resource("ncbi://gene/{gene_id}")
def resource_gene(gene_id: str) -> str:
    """Gene information including genomic locations and functional annotations."""
    try:
        data = _client().gene_by_id(int(gene_id))
        return _truncate_gene_output(_json_text(data))
    except (ValueError, NCBIError) as e:
        return _json_text({"error": str(e), "gene_id": gene_id})


@mcp.resource("ncbi://taxonomy/{tax_id}")
def resource_taxonomy(tax_id: str) -> str:
    """Taxonomic classification and lineage information."""
    try:
        data = _client().taxonomy_taxon(int(tax_id))
        return _json_text(data)
    except (ValueError, NCBIError) as e:
        return _json_text({"error": str(e), "tax_id": tax_id})


@mcp.resource("ncbi://assembly/{assembly_accession}")
def resource_assembly(assembly_accession: str) -> str:
    """Assembly metadata, statistics, and quality metrics."""
    try:
        data = _client().assembly_by_accession(assembly_accession)
        return _json_text(data)
    except NCBIError as e:
        return _json_text({"error": str(e), "assembly_accession": assembly_accession})


@mcp.resource("ncbi://search/genome/{query}")
def resource_search_genome(query: str) -> str:
    """Search genome assemblies by organism or keyword (returns first page)."""
    try:
        # Prefer taxonomy search if query looks like a name, then genome by taxon
        tax_client = _client()
        search_data = tax_client.taxonomy_search(query, limit=5)
        taxa = search_data.get("taxonomy", [])
        if taxa:
            tax_id = taxa[0].get("tax_id")
            if tax_id:
                data = tax_client.genome_taxon_report(tax_id, limit=20)
                return _json_text({"query": query, "data_type": "genome", "results": data})
        return _json_text({"query": query, "data_type": "genome", "message": "No taxonomy match; try search_genomes with a tax_id"})
    except NCBIError as e:
        return _json_text({"error": str(e), "query": query})


# ----- Genome tools -----


@mcp.tool()
def search_genomes(
    tax_id: int,
    assembly_level: str | None = None,
    assembly_source: str | None = None,
    max_results: int = 50,
    page_token: str | None = None,
    exclude_atypical: bool = False,
) -> str:
    """Search genome assemblies by NCBI taxonomy ID and optional filters.
    Use assembly_level: complete, chromosome, scaffold, or contig.
    Use assembly_source: refseq, genbank, or all.
    """
    max_results = min(max(1, max_results), 1000)
    try:
        data = _client().genome_taxon_report(
            tax_id,
            limit=max_results,
            page_token=page_token,
            assembly_level=assembly_level,
            assembly_source=assembly_source,
        )
        out = {
            "total_count": data.get("total_count", 0),
            "returned_count": len(data.get("reports", [])),
            "next_page_token": data.get("next_page_token"),
            "genomes": data.get("reports", []),
        }
        return _json_text(out)
    except NCBIError as e:
        return _json_text({"error": str(e)})


@mcp.tool()
def get_genome_info(accession: str, include_annotation: bool = True) -> str:
    """Get detailed information for a genome assembly by accession (e.g. GCF_000001405.40)."""
    try:
        data = _client().genome_by_accession(accession, include_annotation=include_annotation)
        return _json_text(data)
    except NCBIError as e:
        return _json_text({"error": str(e)})


@mcp.tool()
def get_genome_summary(accession: str) -> str:
    """Get summary statistics for a genome assembly."""
    try:
        data = _client().genome_dataset_report(accession)
        return _json_text({"accession": accession, "summary": data})
    except NCBIError as e:
        return _json_text({"error": str(e)})


@mcp.tool()
def download_genome_data(
    accession: str,
    include_annotation: bool = True,
) -> str:
    """Get download URLs and metadata for genome data files."""
    try:
        data = _client().genome_download(accession, include_annotation=include_annotation)
        return _json_text({"accession": accession, "download_info": data})
    except NCBIError as e:
        return _json_text({"error": str(e)})


# ----- Gene tools -----


@mcp.tool()
def search_genes(
    gene_symbol: str | None = None,
    gene_id: int | None = None,
    organism: str | None = None,
    tax_id: int | None = None,
    chromosome: str | None = None,
    max_results: int = 20,
    page_token: str | None = None,
) -> str:
    """Search genes by symbol, organism/tax_id, or chromosome. Provide at least one of gene_symbol, gene_id, organism, or tax_id.
    For primer target scouting, prefer the search_gene_coordinates tool which returns compact coordinate-only results."""
    if not any([gene_symbol, gene_id is not None, organism, tax_id is not None]):
        return _json_text({"error": "Provide at least one of: gene_symbol, gene_id, organism, tax_id"})
    max_results = min(max(1, max_results), 1000)
    try:
        taxon = str(tax_id) if tax_id is not None else organism
        data = _client().gene_search(
            symbol=gene_symbol,
            taxon=taxon,
            limit=max_results,
            page_token=page_token,
            chromosome=chromosome,
        )
        reports = data.get("reports", data.get("genes", []))
        if gene_id is not None and not gene_symbol:
            reports = [
                r for r in reports
                if str((r.get("gene") or r).get("gene_id", "")) == str(gene_id)
            ]
        out = {
            "total_count": data.get("total_count", len(reports)),
            "returned_count": len(reports),
            "next_page_token": data.get("next_page_token"),
            "genes": reports,
        }
        return _truncate_gene_output(_json_text(out))
    except NCBIError as e:
        return _json_text({"error": str(e)})


@mcp.tool()
def get_gene_info(
    gene_id: int | None = None,
    gene_symbol: str | None = None,
    organism: str | None = None,
    include_sequences: bool = False,
) -> str:
    """Get detailed information for a gene by NCBI Gene ID or by symbol + organism."""
    if gene_id is not None:
        try:
            content = "COMPLETE" if include_sequences else "SUMMARY"
            data = _client().gene_by_id(gene_id, returned_content=content)
            return _truncate_gene_output(_json_text(data))
        except NCBIError as e:
            return _json_text({"error": str(e)})
    if gene_symbol and organism:
        try:
            search_data = _client().gene_search(symbol=gene_symbol, taxon=organism, limit=1)
            reports = search_data.get("reports", search_data.get("genes", []))
            if not reports:
                return _json_text({"error": f"Gene {gene_symbol} not found in {organism}"})
            gene_obj = reports[0].get("gene") or reports[0]
            gid = gene_obj.get("gene_id")
            if not gid:
                return _json_text({"error": "No gene_id in search result"})
            content = "COMPLETE" if include_sequences else "SUMMARY"
            data = _client().gene_by_id(int(gid), returned_content=content)
            return _truncate_gene_output(_json_text(data))
        except NCBIError as e:
            return _json_text({"error": str(e)})
    return _json_text({"error": "Provide either gene_id or (gene_symbol and organism)"})


@mcp.tool()
def get_gene_sequences(
    gene_id: int,
    sequence_type: str | None = None,
) -> str:
    """Retrieve sequences for a gene. sequence_type: genomic, transcript, or protein."""
    try:
        content = "COMPLETE"
        data = _client().gene_by_id(gene_id, returned_content=content)
        out = {"gene_id": gene_id, "sequence_type": sequence_type or "all", "sequences": data}
        return _truncate_gene_output(_json_text(out))
    except NCBIError as e:
        return _json_text({"error": str(e)})


# ----- Primer scout helper -----


def _extract_gene_coords(reports: list[dict]) -> list[dict]:
    """Distill full gene records down to just the fields needed for primer target selection.

    Handles the NCBI Datasets v2 response structure:
      reports[].gene.annotations[].genomic_locations[].genomic_accession_version
      reports[].gene.annotations[].genomic_locations[].genomic_range.{begin, end, orientation}
    """
    results: list[dict] = []
    for report in reports:
        gene_info = report.get("gene") or report
        annotations = gene_info.get("annotations") or []
        for ann in annotations:
            for loc in ann.get("genomic_locations") or []:
                accession = loc.get("genomic_accession_version", "")
                gr = loc.get("genomic_range") or {}
                raw_begin = gr.get("begin")
                raw_end = gr.get("end")
                if raw_begin is None or raw_end is None:
                    continue
                begin = int(raw_begin)
                end = int(raw_end)
                results.append({
                    "gene_id": gene_info.get("gene_id"),
                    "symbol": gene_info.get("symbol", ""),
                    "description": (gene_info.get("description") or "").split(";")[0],
                    "organism": gene_info.get("taxname", ""),
                    "tax_id": gene_info.get("tax_id"),
                    "accession": accession,
                    "seq_start": begin,
                    "seq_stop": end,
                    "orientation": gr.get("orientation", ""),
                    "length": abs(end - begin) + 1,
                })
    return results


@mcp.tool()
def search_gene_coordinates(
    gene_symbol: str | None = None,
    organism: str | None = None,
    tax_id: int | None = None,
    max_results: int = 10,
) -> str:
    """Search genes and return ONLY accession + genomic coordinates — optimised for
    primer target scouting.  Returns compact results that won't be truncated.
    Provide at least gene_symbol or organism/tax_id."""
    if not any([gene_symbol, organism, tax_id is not None]):
        return _json_text({"error": "Provide at least one of: gene_symbol, organism, tax_id"})
    max_results = min(max(1, max_results), 100)
    try:
        taxon = str(tax_id) if tax_id is not None else organism
        data = _client().gene_search(
            symbol=gene_symbol,
            taxon=taxon,
            limit=max_results,
        )
        reports = data.get("reports", data.get("genes", []))
        coords = _extract_gene_coords(reports)
        return _json_text({
            "total_count": data.get("total_count", len(reports)),
            "returned": len(coords),
            "coordinates": coords,
        })
    except NCBIError as e:
        return _json_text({"error": str(e)})


# ----- Efetch tools (raw FASTA sequences) -----


MAX_FASTA_BP = 3000


def _parse_fasta_sequence(fasta_text: str) -> tuple[str, str]:
    """Split FASTA text into (header_line, sequence_only). Strips whitespace."""
    lines = fasta_text.strip().splitlines()
    header = ""
    seq_lines: list[str] = []
    for line in lines:
        if line.startswith(">"):
            header = line
        else:
            seq_lines.append(line.strip())
    return header, "".join(seq_lines)


@mcp.tool()
def fetch_nucleotide_fasta(
    accession: str,
    seq_start: int | None = None,
    seq_stop: int | None = None,
) -> str:
    """Fetch the raw FASTA nucleotide sequence for an accession (e.g. NM_000546.6,
    NC_000017.11, NZ_CP007799.1). Returns the FASTA text (header + ATGC sequence).
    Optionally specify seq_start/seq_stop (1-based) to retrieve a subsequence.
    Sequences longer than 3000 bp are truncated to the first 3000 bp with a warning;
    use seq_start/seq_stop to target a specific region instead."""
    try:
        raw = _client().efetch_fasta(
            accession,
            db="nucleotide",
            seq_start=seq_start,
            seq_stop=seq_stop,
        )
        header, seq = _parse_fasta_sequence(raw)
        if len(seq) > MAX_FASTA_BP:
            truncated = seq[:MAX_FASTA_BP]
            return _json_text({
                "warning": (
                    f"Sequence is {len(seq)} bp which exceeds the {MAX_FASTA_BP} bp limit. "
                    f"Truncated to the first {MAX_FASTA_BP} bp. "
                    "Use seq_start and seq_stop to target the specific gene region you need."
                ),
                "accession": accession,
                "original_length": len(seq),
                "returned_length": MAX_FASTA_BP,
                "header": header,
                "sequence": truncated,
            })
        return _json_text({
            "accession": accession,
            "length": len(seq),
            "header": header,
            "sequence": seq,
        })
    except NCBIError as e:
        return _json_text({"error": str(e), "accession": accession})


@mcp.tool()
def fetch_multiple_fasta(
    accessions: list[str],
) -> str:
    """Fetch raw FASTA nucleotide sequences for multiple accessions in one request
    (max 50). Each sequence longer than 3000 bp is truncated with a warning.
    Returns a JSON array of results."""
    if len(accessions) > 50:
        return _json_text({"error": "Maximum 50 accessions per batch"})
    try:
        raw = _client().efetch_batch_fasta(accessions, db="nucleotide")
    except (ValueError, NCBIError) as e:
        return _json_text({"error": str(e)})

    entries: list[dict] = []
    current_header = ""
    current_lines: list[str] = []

    def _flush() -> None:
        if not current_header and not current_lines:
            return
        seq = "".join(current_lines)
        entry: dict = {"header": current_header, "length": len(seq)}
        if len(seq) > MAX_FASTA_BP:
            entry["warning"] = (
                f"Sequence is {len(seq)} bp, truncated to {MAX_FASTA_BP} bp. "
                "Use fetch_nucleotide_fasta with seq_start/seq_stop for a specific region."
            )
            entry["original_length"] = len(seq)
            entry["returned_length"] = MAX_FASTA_BP
            entry["sequence"] = seq[:MAX_FASTA_BP]
        else:
            entry["sequence"] = seq
        entries.append(entry)

    for line in raw.strip().splitlines():
        if line.startswith(">"):
            _flush()
            current_header = line
            current_lines = []
        else:
            current_lines.append(line.strip())
    _flush()

    return _json_text({"results": entries, "count": len(entries)})


# ----- Taxonomy tools -----


@mcp.tool()
def search_taxonomy(
    query: str,
    rank: str | None = None,
    max_results: int = 50,
) -> str:
    """Search taxonomic information by organism name or keywords."""
    max_results = min(max(1, max_results), 1000)
    try:
        data = _client().taxonomy_search(query, limit=max_results, rank=rank)
        out = {
            "total_count": data.get("total_count", 0),
            "returned_count": len(data.get("taxonomy", [])),
            "taxonomy": data.get("taxonomy", []),
        }
        return _json_text(out)
    except NCBIError as e:
        return _json_text({"error": str(e)})


@mcp.tool()
def get_taxonomy_info(tax_id: int, include_lineage: bool = True) -> str:
    """Get detailed taxonomic information for a taxon by NCBI taxonomy ID."""
    try:
        data = _client().taxonomy_taxon(tax_id, include_lineage=include_lineage)
        return _json_text(data)
    except NCBIError as e:
        return _json_text({"error": str(e)})


@mcp.tool()
def get_taxonomic_lineage(
    tax_id: int,
    include_ranks: bool = True,
    include_synonyms: bool = False,
) -> str:
    """Get complete taxonomic lineage for an organism."""
    try:
        data = _client().taxonomy_lineage(
            tax_id,
            include_ranks=include_ranks,
            include_synonyms=include_synonyms,
        )
        return _json_text({"tax_id": tax_id, "taxonomic_lineage": data})
    except NCBIError as e:
        return _json_text({"error": str(e)})


@mcp.tool()
def get_organism_info(organism: str | None = None, tax_id: int | None = None) -> str:
    """Get organism information and available genome datasets. Provide organism name or tax_id."""
    if not organism and tax_id is None:
        return _json_text({"error": "Provide either organism or tax_id"})
    try:
        if organism and tax_id is None:
            search_data = _client().taxonomy_search(organism, limit=1)
            taxa = search_data.get("taxonomy", [])
            if not taxa:
                return _json_text({"error": f"Organism not found: {organism}"})
            tax_id = taxa[0].get("tax_id")
            if tax_id is None:
                return _json_text({"error": "No tax_id in search result"})
        tax_data = _client().taxonomy_taxon(tax_id)
        genome_data = _client().genome_taxon_report(tax_id, limit=10)
        out = {
            "organism_info": tax_data,
            "available_genomes": genome_data.get("reports", [])[:10],
            "genome_count": genome_data.get("total_count", 0),
        }
        return _json_text(out)
    except NCBIError as e:
        return _json_text({"error": str(e)})


# ----- Assembly tools -----


@mcp.tool()
def search_assemblies(
    query: str | None = None,
    tax_id: int | None = None,
    assembly_level: str | None = None,
    assembly_source: str | None = None,
    exclude_atypical: bool = False,
    max_results: int = 50,
    page_token: str | None = None,
) -> str:
    """Search genome assemblies by query and/or tax_id. Filters: assembly_level, assembly_source (refseq/genbank/all)."""
    max_results = min(max(1, max_results), 1000)
    try:
        data = _client().assembly_search(
            q=query,
            taxon=str(tax_id) if tax_id is not None else None,
            limit=max_results,
            page_token=page_token,
            assembly_level=assembly_level,
            assembly_source=assembly_source,
            exclude_atypical=exclude_atypical,
        )
        out = {
            "total_count": data.get("total_count", 0),
            "returned_count": len(data.get("assemblies", [])),
            "next_page_token": data.get("next_page_token"),
            "assemblies": data.get("assemblies", []),
        }
        return _json_text(out)
    except NCBIError as e:
        return _json_text({"error": str(e)})


@mcp.tool()
def get_assembly_info(
    assembly_accession: str,
    include_annotation: bool = True,
) -> str:
    """Get detailed metadata and statistics for a genome assembly (e.g. GCF_000001405.40)."""
    try:
        data = _client().assembly_by_accession(
            assembly_accession,
            include_annotation=include_annotation,
        )
        return _json_text(data)
    except NCBIError as e:
        return _json_text({"error": str(e)})


@mcp.tool()
def batch_assembly_info(
    accessions: list[str],
    include_annotation: bool = False,
) -> str:
    """Get information for multiple assemblies in one request (max 100)."""
    if len(accessions) > 100:
        return _json_text({"error": "Maximum 100 accessions per batch"})
    try:
        data = _client().assembly_batch(accessions, include_annotation=include_annotation)
        out = {
            "requested_accessions": accessions,
            "assemblies": data.get("assemblies", []),
            "returned_count": len(data.get("assemblies", [])),
        }
        return _json_text(out)
    except (ValueError, NCBIError) as e:
        return _json_text({"error": str(e)})
