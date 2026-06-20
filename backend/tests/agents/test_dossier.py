from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.agents.dossier import (
    MethodologyEntry,
    PaperRecord,
    PaperSource,
    ResearchDossier,
    ResearchGap,
    SearchMetadata,
)


def _make_metadata() -> SearchMetadata:
    return SearchMetadata(
        query="transformer attention mechanism",
        seed_paper_id="seed_abc123",
        sources_queried=["semantic_scholar", "arxiv", "openalex", "crossref"],
        sources_succeeded=["semantic_scholar", "arxiv", "openalex"],
        sources_failed=[{"source": "crossref", "reason": "HTTP 503"}],
        total_papers_found=42,
        papers_after_dedup=18,
        execution_time_ms=1234,
        llm_tokens_used=567,
        estimated_cost_usd=0.0023,
    )


def _make_source() -> PaperSource:
    return PaperSource(
        source="semantic_scholar",
        matched_in=["title", "abstract"],
        fetched_at=datetime(2026, 6, 21, 12, 0, 0),
        raw_id="abc123",
    )


def _make_paper() -> PaperRecord:
    return PaperRecord(
        paper_id="abc123",
        doi="10.48550/arXiv.1706.03762",
        arxiv_id="1706.03762",
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer"],
        year=2017,
        venue="NeurIPS",
        citation_count=95000,
        abstract="We propose the Transformer.",
        sources=[_make_source()],
        relevance_score=0.95,
        recency_score=0.80,
        final_rank=1,
    )


def _make_dossier() -> ResearchDossier:
    return ResearchDossier(
        papers=[_make_paper()],
        gaps=[
            ResearchGap(
                concept_a="sparse attention",
                concept_b="long-context reasoning",
                gap_score=0.72,
                supporting_papers=["abc123"],
                confidence="high",
                description="No work jointly optimises both.",
            )
        ],
        methodologies=[
            MethodologyEntry(
                paper_id="abc123",
                method_name="Multi-Head Attention",
                dataset="WMT 2014 EN-DE",
                metrics=["BLEU"],
                baseline_methods=["LSTM", "GRU"],
                result="28.4 BLEU",
                confidence="high",
            )
        ],
        search_metadata=_make_metadata(),
        generated_at=datetime(2026, 6, 21, 12, 0, 0),
    )


def test_dossier_round_trips_json():
    original = _make_dossier()
    json_payload = original.model_dump_json()
    restored = ResearchDossier.model_validate_json(json_payload)
    assert restored == original


def test_dossier_is_immutable():
    dossier = _make_dossier()
    with pytest.raises(ValidationError):
        dossier.papers = []  # type: ignore[misc]


def test_dossier_default_schema_version():
    dossier = _make_dossier()
    assert dossier.schema_version == "1.0"


def test_dossier_from_search_results_backfill():
    legacy_results = [
        {
            "title": "Attention Is All You Need",
            "authors": ["Ashish Vaswani", "Noam Shazeer"],
            "year": 2017,
            "source": "semantic_scholar",
            "citation_count": 95000,
            "abstract": "The dominant sequence transduction models.",
            "doi": "10.48550/arXiv.1706.03762",
            "url": "https://arxiv.org/abs/1706.03762",
        },
        {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "authors": ["Jacob Devlin"],
            "year": 2019,
            "source": "arxiv",
            "citation_count": 70000,
            "abstract": "We introduce BERT.",
            "doi": None,
            "url": "https://arxiv.org/abs/1810.04805",
        },
    ]

    dossier = ResearchDossier.from_search_results(
        legacy_results,
        query="transformer attention",
        generated_at=datetime(2026, 6, 21, 12, 0, 0),
    )

    assert dossier.schema_version == "1.0"
    assert isinstance(dossier.generated_at, datetime)
    assert len(dossier.papers) == 2

    p0 = dossier.papers[0]
    assert p0.title == "Attention Is All You Need"
    assert p0.year == 2017
    assert p0.citation_count == 95000
    assert p0.doi == "10.48550/arXiv.1706.03762"
    assert p0.sources and p0.sources[0].source == "semantic_scholar"

    p1 = dossier.papers[1]
    assert p1.title.startswith("BERT")
    assert p1.sources[0].source == "arxiv"
    assert p1.arxiv_id == "1810.04805"
