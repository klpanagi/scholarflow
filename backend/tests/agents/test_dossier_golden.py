from __future__ import annotations

from pathlib import Path

from app.agents.dossier import ResearchDossier

GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_PATH = GOLDEN_DIR / "dossier_v1.json"


def _load_golden_json() -> str:
    return GOLDEN_PATH.read_text(encoding="utf-8")


def test_golden_dossier_validates():
    golden_json = _load_golden_json()
    dossier = ResearchDossier.model_validate_json(golden_json)
    assert dossier.schema_version == "1.0"
    assert len(dossier.papers) == 3

    # Paper 1: DOI + S2 ID + citation count + abstract
    p1 = dossier.papers[0]
    assert p1.doi == "10.1109/CVPR.2016.90"
    assert p1.arxiv_id is None
    assert p1.citation_count > 0
    assert p1.abstract is not None
    assert len(p1.authors) >= 3
    assert p1.year == 2016
    assert p1.venue is not None
    assert len(p1.sources) == 1
    assert p1.sources[0].source == "semantic_scholar"
    assert p1.final_rank == 0

    # Paper 2: arXiv ID only + no DOI + no abstract (partial data)
    p2 = dossier.papers[1]
    assert p2.arxiv_id == "1706.03762"
    assert p2.doi is None
    assert p2.abstract is None
    assert p2.citation_count == 0
    assert p2.venue is None
    assert len(p2.sources) == 1
    assert p2.sources[0].source == "arxiv"
    assert p2.final_rank == 1

    # Paper 3: openalex source + venue + multi-source matches
    p3 = dossier.papers[2]
    assert p3.arxiv_id == "2005.14165"
    assert p3.doi == "10.1038/s41586-020-2649-2"
    assert p3.abstract is not None
    assert p3.venue == "NeurIPS 2020"
    assert len(p3.sources) == 2
    assert {s.source for s in p3.sources} == {"semantic_scholar", "openalex"}
    assert p3.final_rank == 2

    # Top-level lists
    assert isinstance(dossier.gaps, list)
    assert isinstance(dossier.methodologies, list)
    assert len(dossier.gaps) >= 1
    assert len(dossier.methodologies) >= 1

    # Search metadata
    meta = dossier.search_metadata
    assert meta is not None
    assert isinstance(meta.query, str) and len(meta.query) > 0
    assert isinstance(meta.sources_queried, list) and len(meta.sources_queried) >= 1
    assert isinstance(meta.sources_succeeded, list)
    assert isinstance(meta.sources_failed, list)
    assert meta.total_papers_found >= len(dossier.papers)
    assert meta.papers_after_dedup == len(dossier.papers)
    assert meta.execution_time_ms > 0

    # Timestamp and legacy shim
    assert dossier.generated_at is not None
    assert dossier.legacy_search_results is None


def test_golden_dossier_round_trip():
    golden_json = _load_golden_json()
    original = ResearchDossier.model_validate_json(golden_json)

    serialized = original.model_dump_json()
    restored = ResearchDossier.model_validate_json(serialized)

    assert restored == original

    original_keys = set(original.model_dump(exclude_unset=True).keys())
    restored_keys = set(restored.model_dump(exclude_unset=True).keys())
    assert restored_keys == original_keys
