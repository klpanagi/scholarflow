"""Tests for fuzzy paper deduplication module."""

import pytest

from app.agents.dedup import (
    are_titles_duplicate,
    deduplicate_papers,
    extract_arxiv_id,
    levenshtein,
    normalize_title,
)


class TestNormalizeTitle:
    def test_normalize_title_strips_punctuation(self) -> None:
        """Punctuation stripped, lowercased, whitespace collapsed."""
        assert normalize_title("Attention IS All You Need!") == "attention is all you need"


class TestLevenshtein:
    def test_levenshtein_basic(self) -> None:
        """Classic kitten→sitting distance is 3."""
        assert levenshtein("kitten", "sitting") == 3


class TestAreTitlesDuplicate:
    def test_are_titles_duplicate_within_threshold(self) -> None:
        """Titles differing by trailing punctuation are duplicates."""
        assert are_titles_duplicate("Attention Is All You Need", "Attention Is All You Need.") is True


class TestDeduplicatePapers:
    def test_dedup_merges_by_doi(self) -> None:
        """Three papers with the same DOI → one result with merged_sources length 3."""
        papers = [
            {"doi": "10.1234/test", "title": "Test Paper", "source": "semantic_scholar", "citation_count": 100},
            {"doi": "10.1234/test", "title": "Test Paper", "source": "openalex", "abstract": "Abstract A"},
            {"doi": "10.1234/test", "title": "Test Paper", "source": "crossref", "citation_count": 50},
        ]
        result = deduplicate_papers(papers)
        assert len(result) == 1
        assert sorted(result[0]["merged_sources"]) == ["crossref", "openalex", "semantic_scholar"]

    def test_dedup_merges_by_arxiv_id(self) -> None:
        """Two papers with the same arXiv ID but different DOIs → one result."""
        papers = [
            {"arxiv_id": "2005.14165", "doi": "10.1/aaa", "title": "GPT-3", "source": "semantic_scholar"},
            {"arxiv_id": "2005.14165", "doi": None, "title": "GPT-3", "source": "openalex", "abstract": "Abs"},
        ]
        result = deduplicate_papers(papers)
        assert len(result) == 1

    def test_dedup_handles_levenshtein_typos(self) -> None:
        """Papers with Levenshtein distance ≤ 2 in title are merged."""
        papers = [
            {"title": "Transfomer Architecture", "source": "arxiv"},
            {"title": "Transformer Architecture", "source": "semantic_scholar", "citation_count": 42},
        ]
        result = deduplicate_papers(papers)
        assert len(result) == 1

    def test_dedup_preserves_richest_metadata(self) -> None:
        """S2 citation_count + OpenAlex abstract → merged has both."""
        papers = [
            {
                "doi": "10.1/abc",
                "title": "Test",
                "source": "semantic_scholar",
                "citation_count": 100,
                "abstract": None,
            },
            {
                "doi": "10.1/abc",
                "title": "Test",
                "source": "openalex",
                "citation_count": 95,
                "abstract": "Long abstract text here.",
            },
        ]
        result = deduplicate_papers(papers)
        assert len(result) == 1
        merged = result[0]
        assert merged["citation_count"] == 100
        assert merged["abstract"] == "Long abstract text here."
