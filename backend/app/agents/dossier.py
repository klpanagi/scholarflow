"""ResearchDossier v1.0 schema for the ScholarAgent enhancement.

Defines the structured output of multi-source academic search. The dossier is
immutable (frozen=True) and is the contract between the search phase and
downstream synthesis (gaps, methodologies, recommendations, markdown render).

Backward compatibility: `ResearchDossier.from_search_results` accepts the
legacy `context["search_results"]` list-of-dicts shape produced by the
pre-Wave 1 ScholarAgent and lifts it into the v1.0 schema.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SourceName = Literal[
    "semantic_scholar",
    "arxiv",
    "openalex",
    "crossref",
    "internal",
]

Confidence = Literal["high", "medium", "low"]


class PaperSource(BaseModel):
    """Provenance record for a single retrieval of a paper from one source."""

    source: SourceName = Field(
        description="Identifier of the academic API the paper was retrieved from",
    )
    matched_in: list[str] = Field(
        description=(
            "Query fields in which the paper matched, e.g. 'title', 'abstract', "
            "'author', 'venue'"
        ),
    )
    fetched_at: datetime = Field(
        description="Naive UTC timestamp at which the source returned this paper",
    )
    raw_id: str = Field(
        description=(
            "Source-native identifier (DOI, arXiv ID, OpenAlex ID, S2 paper ID, "
            "or URL) used to fetch the record"
        ),
    )


class PaperRecord(BaseModel):
    """Canonical, de-duplicated representation of a single academic paper."""

    paper_id: str = Field(
        description=(
            "Stable canonical identifier for the paper. Prefer Semantic Scholar "
            "paper ID; fall back to DOI or arXiv ID when S2 ID is unavailable"
        ),
    )
    doi: str | None = Field(
        default=None,
        description="Digital Object Identifier of the paper, if known",
    )
    arxiv_id: str | None = Field(
        default=None,
        description="arXiv identifier (e.g. '1706.03762') of the paper, if known",
    )
    title: str = Field(description="Full paper title as returned by the source")
    authors: list[str] = Field(
        description="Ordered list of author display names",
    )
    year: int | None = Field(
        default=None,
        description="Four-digit publication year; None if unknown",
    )
    venue: str | None = Field(
        default=None,
        description="Publication venue (journal name, conference name, or preprint repository)",
    )
    citation_count: int = Field(
        default=0,
        description="Total inbound citation count at fetch time; 0 if unknown",
    )
    abstract: str | None = Field(
        default=None,
        description="Paper abstract text, or None if unavailable",
    )
    sources: list[PaperSource] = Field(
        default_factory=list,
        description=(
            "All retrieval events for this paper across sources. Multi-source "
            "matches produce multiple entries"
        ),
    )
    relevance_score: float = Field(
        default=0.0,
        description=(
            "Heuristic relevance in [0.0, 1.0] estimating how well the paper "
            "matches the user query; computed by the search phase"
        ),
    )
    recency_score: float = Field(
        default=0.0,
        description=(
            "Heuristic recency in [0.0, 1.0] with 1.0 = current year; used as a "
            "secondary ranking signal"
        ),
    )
    final_rank: int = Field(
        default=0,
        description=(
            "Zero-based position in the final ranked paper list after all "
            "filtering and scoring; 0 when ranking has not been performed"
        ),
    )


class ResearchGap(BaseModel):
    """A concept-level gap surfaced from cross-paper analysis."""

    concept_a: str = Field(
        description="First concept or technique appearing in the literature",
    )
    concept_b: str = Field(
        description="Second concept or technique appearing in the literature",
    )
    gap_score: float = Field(
        description=(
            "Score in [0.0, 1.0] quantifying the strength of the gap; higher = "
            "more under-explored intersection"
        ),
    )
    supporting_papers: list[str] = Field(
        description=(
            "Canonical paper_ids of papers that mention concept_a and/or "
            "concept_b but do not bridge them"
        ),
    )
    confidence: Confidence = Field(
        description="Confidence level of the gap assessment: 'high', 'medium', or 'low'",
    )
    description: str = Field(
        description="One-sentence human-readable explanation of the gap",
    )


class MethodologyEntry(BaseModel):
    """A method-vs-baseline result row extracted from a paper."""

    paper_id: str = Field(
        description="Canonical paper_id (PaperRecord.paper_id) this row is sourced from",
    )
    method_name: str = Field(
        description="Name of the proposed/analysed method as written in the paper",
    )
    dataset: str = Field(
        description="Dataset or benchmark on which the result was measured",
    )
    metrics: list[str] = Field(
        description="Metric names reported in the result row, e.g. ['BLEU', 'ROUGE-L']",
    )
    baseline_methods: list[str] = Field(
        description="Names of baseline methods the proposed method is compared against",
    )
    result: str = Field(
        description="Reported result string, e.g. '28.4 BLEU' or '91.2% accuracy'",
    )
    confidence: Confidence = Field(
        description="Confidence that the extracted row is correct: 'high', 'medium', or 'low'",
    )


class SearchMetadata(BaseModel):
    """Operational metadata describing a single multi-source search run."""

    query: str = Field(description="Free-text user query that triggered the search")
    seed_paper_id: str | None = Field(
        default=None,
        description=(
            "Canonical paper_id of a seed paper when the search is paper-centric "
            "(e.g. citing/reference expansion); None for pure keyword queries"
        ),
    )
    sources_queried: list[SourceName] = Field(
        description="All sources attempted during the search run",
    )
    sources_succeeded: list[SourceName] = Field(
        description="Sources that returned at least one paper",
    )
    sources_failed: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "Per-source failure records; each dict contains 'source' (the source "
            "name) and 'reason' (a short human-readable failure reason)"
        ),
    )
    total_papers_found: int = Field(
        description="Sum of papers returned by all sources, before deduplication",
    )
    papers_after_dedup: int = Field(
        description="Number of unique papers after cross-source deduplication",
    )
    execution_time_ms: int = Field(
        description="Wall-clock search duration in milliseconds",
    )
    llm_tokens_used: int = Field(
        default=0,
        description="Total LLM tokens consumed during the search run (0 if no LLM used)",
    )
    estimated_cost_usd: float = Field(
        default=0.0,
        description="Estimated LLM cost in USD for the search run",
    )


class ResearchDossier(BaseModel):
    """Top-level structured output of the ScholarAgent search phase.

    The dossier is immutable: assigning to any field raises ValidationError.
    To produce a modified copy, use `model_copy(update=...)`.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["1.0"] = Field(
        default="1.0",
        description="Dossier schema version. Bumped on breaking changes to any sub-model",
    )
    papers: list[PaperRecord] = Field(
        default_factory=list,
        description="Final ranked, deduplicated paper list",
    )
    gaps: list[ResearchGap] = Field(
        default_factory=list,
        description="Research gaps surfaced from cross-paper analysis",
    )
    methodologies: list[MethodologyEntry] = Field(
        default_factory=list,
        description="Method-vs-baseline result rows extracted from the papers",
    )
    search_metadata: SearchMetadata | None = Field(
        default=None,
        description=(
            "Operational metadata for the search run; None when the dossier is "
            "constructed outside a live search (e.g. tests or backfill)"
        ),
    )
    generated_at: datetime = Field(
        description="Naive UTC timestamp at which this dossier was produced",
    )
    legacy_search_results: list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            "Backward-compatibility shim. Holds the raw pre-Wave 1 "
            "context['search_results'] payload when the dossier is built via "
            "from_search_results; None for freshly produced dossiers"
        ),
    )

    @classmethod
    def from_search_results(
        cls,
        search_results: list[dict[str, Any]],
        query: str,
        generated_at: datetime | None = None,
    ) -> ResearchDossier:
        """Build a ResearchDossier from the legacy search_results list-of-dicts.

        Each entry is mapped to a PaperRecord. The arxiv_id is extracted from
        a `url` like `https://arxiv.org/abs/1706.03762` when no explicit
        arxiv_id field is present. The legacy payload is preserved in
        `legacy_search_results` for callers that still need raw access.
        """
        now = datetime.now()
        ts = generated_at if generated_at is not None else now

        papers: list[PaperRecord] = []
        sources_queried: list[SourceName] = []
        for raw in search_results:
            if not isinstance(raw, dict):
                continue

            source_name = _coerce_source_name(raw.get("source"))
            if source_name is not None and source_name not in sources_queried:
                sources_queried.append(source_name)

            doi = raw.get("doi")
            arxiv_id = raw.get("arxiv_id")
            url = raw.get("url")
            if not arxiv_id and isinstance(url, str):
                arxiv_id = _extract_arxiv_id_from_url(url)

            paper_id = _resolve_paper_id(
                doi=doi if isinstance(doi, str) else None,
                arxiv_id=arxiv_id,
                paper_id=raw.get("paper_id"),
                url=url if isinstance(url, str) else None,
                title=raw.get("title") if isinstance(raw.get("title"), str) else None,
            )

            raw_id = (
                doi
                if isinstance(doi, str) and doi
                else arxiv_id
                if isinstance(arxiv_id, str) and arxiv_id
                else url
                if isinstance(url, str) and url
                else raw.get("title")
                if isinstance(raw.get("title"), str)
                else ""
            )

            source_entry: PaperSource | None = None
            if source_name is not None:
                source_entry = PaperSource(
                    source=source_name,
                    matched_in=["title"],
                    fetched_at=ts,
                    raw_id=raw_id or "",
                )

            year = raw.get("year")
            try:
                year_int: int | None = int(year) if year is not None else None
            except (TypeError, ValueError):
                year_int = None

            citation_count = raw.get("citation_count", 0) or 0
            try:
                citation_count_int = int(citation_count)
            except (TypeError, ValueError):
                citation_count_int = 0

            authors = raw.get("authors") or []
            if not isinstance(authors, list):
                authors = [str(authors)]
            authors = [str(a) for a in authors]

            paper = PaperRecord(
                paper_id=paper_id,
                doi=doi if isinstance(doi, str) else None,
                arxiv_id=arxiv_id if isinstance(arxiv_id, str) else None,
                title=raw.get("title") or "",
                authors=authors,
                year=year_int,
                venue=raw.get("venue") if isinstance(raw.get("venue"), str) else None,
                citation_count=citation_count_int,
                abstract=raw.get("abstract") if isinstance(raw.get("abstract"), str) else None,
                sources=[source_entry] if source_entry is not None else [],
                relevance_score=0.0,
                recency_score=0.0,
                final_rank=0,
            )
            papers.append(paper)

        metadata = SearchMetadata(
            query=query,
            seed_paper_id=None,
            sources_queried=sources_queried,
            sources_succeeded=sources_queried,
            sources_failed=[],
            total_papers_found=len(papers),
            papers_after_dedup=len(papers),
            execution_time_ms=0,
            llm_tokens_used=0,
            estimated_cost_usd=0.0,
        )

        return cls(
            papers=papers,
            gaps=[],
            methodologies=[],
            search_metadata=metadata,
            generated_at=ts,
            legacy_search_results=list(search_results),
        )


_ARXIV_ABS_RE = re.compile(r"arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5})(v[0-9]+)?", re.IGNORECASE)


def _extract_arxiv_id_from_url(url: str) -> str | None:
    """Return the arXiv ID embedded in an abs/pdf URL, or None."""
    match = _ARXIV_ABS_RE.search(url)
    if match is None:
        return None
    return match.group(1)


def _coerce_source_name(value: Any) -> SourceName | None:
    """Map a free-form source label to the SourceName literal, or None."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    mapping: dict[str, SourceName] = {
        "semantic_scholar": "semantic_scholar",
        "s2": "semantic_scholar",
        "arxiv": "arxiv",
        "openalex": "openalex",
        "crossref": "crossref",
        "internal": "internal",
    }
    return mapping.get(normalized)


def _resolve_paper_id(
    *,
    doi: str | None,
    arxiv_id: str | None,
    paper_id: str | None,
    url: str | None,
    title: str | None,
) -> str:
    """Pick a stable canonical paper_id, preferring DOI > arXiv > S2 ID > URL > title."""
    if doi:
        return doi
    if arxiv_id:
        return f"arxiv:{arxiv_id}"
    if paper_id:
        return paper_id
    if url:
        return url
    if title:
        return f"title:{title}"
    return ""
