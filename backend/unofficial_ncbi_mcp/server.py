"""FastMCP server: tools and resources for NCBI Datasets API."""

from __future__ import annotations

import json
import os
from typing import Any

from fastmcp import FastMCP

from .client import NCBIClient, NCBIError

mcp = FastMCP(
    name="ncbi-datasets",
    version="2.0.0",
)


def _client() -> NCBIClient:
    return NCBIClient()


def _json_text(obj: Any) -> str:
    return json.dumps(obj, indent=2)


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
        return _json_text(data)
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
    max_results: int = 50,
    page_token: str | None = None,
) -> str:
    """Search genes by symbol, organism/tax_id, or chromosome. Provide at least one of gene_symbol, gene_id, organism, or tax_id."""
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
        genes = data.get("genes", [])
        if gene_id is not None and not gene_symbol:
            genes = [g for g in genes if g.get("gene_id") == gene_id]
        out = {
            "total_count": data.get("total_count", len(genes)),
            "returned_count": len(genes),
            "next_page_token": data.get("next_page_token"),
            "genes": genes,
        }
        return _json_text(out)
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
            return _json_text(data)
        except NCBIError as e:
            return _json_text({"error": str(e)})
    if gene_symbol and organism:
        try:
            search_data = _client().gene_search(symbol=gene_symbol, taxon=organism, limit=1)
            genes = search_data.get("genes", [])
            if not genes:
                return _json_text({"error": f"Gene {gene_symbol} not found in {organism}"})
            gid = genes[0].get("gene_id")
            if not gid:
                return _json_text({"error": "No gene_id in search result"})
            content = "COMPLETE" if include_sequences else "SUMMARY"
            data = _client().gene_by_id(gid, returned_content=content)
            return _json_text(data)
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
        return _json_text(out)
    except NCBIError as e:
        return _json_text({"error": str(e)})


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
