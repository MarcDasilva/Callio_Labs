"""NCBI Datasets API v2 HTTP client."""

from __future__ import annotations

import os
import json
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.ncbi.nlm.nih.gov/datasets/v2"
EFETCH_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TIMEOUT = 30.0


class NCBIError(Exception):
    """Raised when an NCBI API request fails."""

    def __init__(self, message: str, status_code: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class NCBIClient:
    """HTTP client for NCBI Datasets v2 REST API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (base_url or os.environ.get("NCBI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key or os.environ.get("NCBI_API_KEY")
        self.timeout = timeout or float(os.environ.get("NCBI_TIMEOUT", DEFAULT_TIMEOUT))
        self._client: httpx.Client | None = None

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "NCBI-Datasets-MCP/2.0",
        }
        if self.api_key:
            headers["api-key"] = self.api_key
        return headers

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._get_headers(),
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        try:
            resp = self.client.request(method, url, params=params, json=json)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            body = e.response.text
            raise NCBIError(
                f"NCBI API error: {e.response.status_code} — {body[:500]}",
                status_code=e.response.status_code,
                body=body,
            ) from e
        except httpx.RequestError as e:
            raise NCBIError(f"Request failed: {e}") from e

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        return self._request("POST", path, params=params, json=json)

    # --- Genome ---

    def genome_by_accession(self, accession: str, include_annotation: bool = True) -> dict[str, Any]:
        path = f"/genome/accession/{accession}"
        params = {}
        if include_annotation:
            params["include_annotation_type"] = "GENOME_GFF,GENOME_GBFF"
        return self.get(path, params=params or None)

    def genome_dataset_report(self, accession: str) -> dict[str, Any]:
        return self.get(f"/genome/accession/{accession}/dataset_report")

    def genome_taxon_report(
        self,
        tax_id: int,
        *,
        limit: int = 50,
        page_token: str | None = None,
        assembly_level: str | None = None,
        assembly_source: str | None = None,
    ) -> dict[str, Any]:
        path = f"/genome/taxon/{tax_id}/dataset_report"
        params: dict[str, Any] = {"limit": limit}
        if page_token:
            params["page_token"] = page_token
        if assembly_level:
            params["assembly_level"] = assembly_level
        if assembly_source and assembly_source != "all":
            params["assembly_source"] = assembly_source
        return self.get(path, params=params)

    def genome_download(self, accession: str, include_annotation: bool = True) -> dict[str, Any]:
        path = f"/genome/accession/{accession}/download"
        params = {}
        if include_annotation:
            params["include_annotation_type"] = "GENOME_GFF,GENOME_GBFF"
        return self.get(path, params=params or None)

    # --- Gene ---

    def gene_by_id(self, gene_id: int, returned_content: str = "SUMMARY") -> dict[str, Any]:
        params = {"returned_content": returned_content}
        return self.get(f"/gene/id/{gene_id}", params=params)

    def gene_search(
        self,
        *,
        symbol: str | None = None,
        taxon: str | None = None,
        limit: int = 50,
        page_token: str | None = None,
        chromosome: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page_size": limit}
        if page_token:
            params["page_token"] = page_token

        if symbol and taxon:
            path = f"/gene/symbol/{symbol}/taxon/{taxon}"
        elif taxon:
            path = f"/gene/taxon/{taxon}"
        elif symbol:
            path = f"/gene/symbol/{symbol}/taxon/human"
        else:
            return {"reports": [], "total_count": 0}

        return self.get(path, params=params)

    # --- Taxonomy ---

    def taxonomy_taxon(self, tax_id: int, include_lineage: bool = True) -> dict[str, Any]:
        params = {"include_lineage": str(include_lineage).lower()}
        return self.get(f"/taxonomy/taxon/{tax_id}", params=params)

    def taxonomy_search(
        self,
        q: str,
        *,
        limit: int = 50,
        rank: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"q": q, "limit": limit}
        if rank:
            params["rank"] = rank
        return self.get("/taxonomy/search", params=params)

    def taxonomy_lineage(
        self,
        tax_id: int,
        *,
        include_ranks: bool = True,
        include_synonyms: bool = False,
    ) -> dict[str, Any]:
        params = {
            "include_ranks": str(include_ranks).lower(),
            "include_synonyms": str(include_synonyms).lower(),
        }
        return self.get(f"/taxonomy/taxon/{tax_id}/lineage", params=params)

    # --- Assembly ---

    def assembly_by_accession(
        self,
        assembly_accession: str,
        include_annotation: bool = True,
    ) -> dict[str, Any]:
        path = f"/assembly/accession/{assembly_accession}"
        params = {}
        if include_annotation:
            params["include_annotation_type"] = "GENOME_GFF,GENOME_GBFF"
        return self.get(path, params=params or None)

    def assembly_search(
        self,
        *,
        q: str | None = None,
        taxon: str | int | None = None,
        limit: int = 50,
        page_token: str | None = None,
        assembly_level: str | None = None,
        assembly_source: str | None = None,
        exclude_atypical: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if q:
            params["q"] = q
        if taxon is not None:
            params["taxon"] = str(taxon)
        if page_token:
            params["page_token"] = page_token
        if assembly_level:
            params["assembly_level"] = assembly_level
        if assembly_source and assembly_source != "all":
            params["assembly_source"] = assembly_source
        if exclude_atypical:
            params["exclude_atypical"] = "true"
        return self.get("/assembly/search", params=params)

    def assembly_batch(
        self,
        accessions: list[str],
        include_annotation: bool = False,
    ) -> dict[str, Any]:
        if len(accessions) > 100:
            raise ValueError("Maximum 100 accessions per batch")
        params: dict[str, Any] = {"accessions": ",".join(accessions)}
        if include_annotation:
            params["include_annotation_type"] = "GENOME_GFF,GENOME_GBFF"
        # NCBI Datasets v2: GET with comma-separated accessions
        return self.get("/assembly/accession", params=params)

    # --- Efetch (Entrez E-Utilities) ---

    def efetch_fasta(
        self,
        accession: str,
        db: str = "nucleotide",
        seq_start: int | None = None,
        seq_stop: int | None = None,
    ) -> str:
        """Fetch a raw FASTA sequence from NCBI Entrez Efetch.

        Returns the plain-text FASTA string (header + sequence).
        """
        params: dict[str, Any] = {
            "db": db,
            "id": accession,
            "rettype": "fasta",
            "retmode": "text",
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if seq_start is not None:
            params["seq_start"] = seq_start
        if seq_stop is not None:
            params["seq_stop"] = seq_stop

        url = f"{EFETCH_BASE_URL}/efetch.fcgi"
        try:
            resp = httpx.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPStatusError as e:
            raise NCBIError(
                f"Efetch error: {e.response.status_code} — {e.response.text[:500]}",
                status_code=e.response.status_code,
                body=e.response.text,
            ) from e
        except httpx.RequestError as e:
            raise NCBIError(f"Efetch request failed: {e}") from e

    def efetch_batch_fasta(
        self,
        accessions: list[str],
        db: str = "nucleotide",
    ) -> str:
        """Fetch FASTA sequences for multiple accessions in a single request."""
        if len(accessions) > 50:
            raise ValueError("Maximum 50 accessions per batch efetch")
        return self.efetch_fasta(",".join(accessions), db=db)
