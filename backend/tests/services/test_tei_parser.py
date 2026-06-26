"""Unit tests for the GROBID TEI XML parser in pdf_service."""

from pathlib import Path

import pytest

from app.services.pdf_service import GrobidResult, parse_tei, pdf_service

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "grobid" / "sample_tei.xml"


@pytest.fixture
def tei_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


@pytest.fixture
def parsed(tei_bytes: bytes) -> GrobidResult:
    return parse_tei(tei_bytes)


@pytest.mark.unit_db
def test_parse_title(parsed: GrobidResult) -> None:
    assert parsed.title == "Sample Paper Title"


@pytest.mark.unit_db
def test_parse_authors_count(parsed: GrobidResult) -> None:
    assert len(parsed.authors) == 3
    assert parsed.authors[0] == "Doe, Jane"
    assert parsed.authors[1] == "Smith, John"
    assert parsed.authors[2] == "García, María"


@pytest.mark.unit_db
def test_parse_abstract(parsed: GrobidResult) -> None:
    assert parsed.abstract
    assert "abstract text" in parsed.abstract.lower()


@pytest.mark.unit_db
def test_parse_doi_and_year(parsed: GrobidResult) -> None:
    assert parsed.doi == "10.1234/sample.2024.001"
    assert parsed.year == 2024
    assert parsed.venue == "Journal of Examples"


@pytest.mark.unit_db
def test_parse_sections_count(parsed: GrobidResult) -> None:
    assert len(parsed.sections) == 3
    headings = [s["heading"] for s in parsed.sections]
    assert headings == ["1. Introduction", "2. Method", "3. Results"]
    for section in parsed.sections:
        assert section["text"].strip()


@pytest.mark.unit_db
def test_parse_references_count(parsed: GrobidResult) -> None:
    assert len(parsed.references) >= 5
    for ref in parsed.references:
        assert ref["raw_text"].strip()
        assert "doi" in ref
        assert "year" in ref
        assert "authors" in ref
        assert "title" in ref


@pytest.mark.unit_db
async def test_extract_citations_returns_refs(tei_bytes: bytes, parsed: GrobidResult) -> None:
    result = await pdf_service.extract_citations(tei_bytes)
    assert isinstance(result, list)
    assert result == parsed.references


@pytest.mark.unit_db
async def test_extract_citations_accepts_str(tei_bytes: bytes) -> None:
    result = await pdf_service.extract_citations(tei_bytes.decode("utf-8"))
    assert len(result) >= 5


@pytest.mark.unit_db
async def test_malformed_xml_returns_empty() -> None:
    result = await pdf_service.extract_citations(b"<not-valid-xml")
    assert result == []


@pytest.mark.unit_db
def test_malformed_xml_parse_tei_raises() -> None:
    with pytest.raises(Exception):
        parse_tei(b"<not-valid-xml")


@pytest.mark.unit_db
def test_grobid_result_roundtrip(parsed: GrobidResult) -> None:
    restored = GrobidResult.from_dict(parsed.to_dict())
    assert restored.title == parsed.title
    assert restored.authors == parsed.authors
    assert restored.abstract == parsed.abstract
    assert restored.doi == parsed.doi
    assert restored.year == parsed.year
    assert restored.venue == parsed.venue
    assert restored.sections == parsed.sections
    assert restored.references == parsed.references
    assert restored.source == parsed.source

