"""Structural tests for the paper-review skill split (B.5 + B.6).

After the GROBID integration split, ``_SKILL_SEEDS`` in
``app.seeds.scholarflow_skills.py`` defines four paper-review-related skills:

* ``solo-paper-review``     — standalone 7-stage pipeline (unchanged)
* ``paper-review``          — workflow-integrated evaluation (unchanged)
* ``paper-review-analyze``  — analyze stage: SearchAgent + ReviewAgent
                              (new, B.5 — extract_citations bound)
* ``paper-review-write``    — write stage: DebateAgent + ReviewWriterAgent
                              (new, B.6 — extract_citations NOT bound)

These tests are pure unit checks against the seed file: no DB, no mocks,
no fixtures beyond the in-process import. Marked ``unit_db`` so the
autouse ``clean_db`` fixture in ``tests/conftest.py`` skips DB setup.
"""

import pytest

from app.seeds.scholarflow_skills import _SKILL_SEEDS

# Build the name -> seed lookup once at import time. Mirrors the style of
# tests/seeds/test_scholarflow_skills.py, which also imports the seed
# constant at module scope.
_SKILLS_BY_NAME: dict[str, dict] = {s["name"]: s for s in _SKILL_SEEDS}

_EXPECTED_BUILTIN_TOOLS: dict[str, list[str]] = {
    # B.5 — analyze stage: GROBID bound for SearchAgent + ReviewAgent
    "paper-review-analyze": ["extract_citations"],
    # B.6 — write stage: no GROBID binding for DebateAgent + ReviewWriterAgent
    "paper-review-write": [],
    # Guard — original workflow-integrated skill remains empty
    "paper-review": [],
    # Guard — standalone pipeline keeps its full tool set
    "solo-paper-review": [
        "search_papers",
        "extract_pdf_text",
        "extract_citations",
        "format_citation",
        "find_citation",
    ],
}


# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
@pytest.mark.parametrize(
    "skill_name",
    sorted(_EXPECTED_BUILTIN_TOOLS),
    ids=lambda n: f"exists:{n}",
)
def test_paper_review_skill_seeds_exist(skill_name: str) -> None:
    """All four paper-review-related skill seeds are present in the seeder."""
    assert skill_name in _SKILLS_BY_NAME, (
        f"Missing skill seed '{skill_name}' in _SKILL_SEEDS. "
        f"Available names: {sorted(_SKILLS_BY_NAME)}"
    )


# ---------------------------------------------------------------------------
# builtin_tools — parametrized structural assertion
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
@pytest.mark.parametrize(
    ("skill_name", "expected_tools"),
    [(name, tools) for name, tools in sorted(_EXPECTED_BUILTIN_TOOLS.items())],
    ids=[
        "analyze-has-extract_citations",
        "original-empty",
        "solo-full-toolset",
        "write-no-extract_citations",
    ],
)
def test_paper_review_skill_builtin_tools_match(
    skill_name: str, expected_tools: list[str]
) -> None:
    """Each paper-review skill carries exactly the expected builtin_tools list.

    This single parametrized test covers:

    * **B.5** (positive): ``paper-review-analyze`` includes ``extract_citations``
    * **B.6** (negative): ``paper-review-write`` excludes ``extract_citations``
    * Guards: ``paper-review`` and ``solo-paper-review`` are unchanged
    """
    skill = _SKILLS_BY_NAME[skill_name]
    assert skill["builtin_tools"] == expected_tools, (
        f"Skill '{skill_name}' builtin_tools mismatch: "
        f"expected {expected_tools!r}, got {skill['builtin_tools']!r}"
    )


# ---------------------------------------------------------------------------
# B.5 — positive: analyze stage has GROBID
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
def test_paper_review_analyze_includes_extract_citations() -> None:
    """B.5: ``paper-review-analyze`` MUST include ``extract_citations``.

    Bound to the SearchAgent and ReviewAgent stages via
    ``agent_skills_table``; without this tool, the analyze stage cannot
    request structured GROBID bibliography extraction.
    """
    skill = _SKILLS_BY_NAME["paper-review-analyze"]
    assert "extract_citations" in skill["builtin_tools"], (
        f"Expected 'extract_citations' in paper-review-analyze.builtin_tools, "
        f"got {skill['builtin_tools']!r}"
    )


# ---------------------------------------------------------------------------
# B.6 — negative: write stage has NO GROBID
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
def test_paper_review_write_excludes_extract_citations() -> None:
    """B.6: ``paper-review-write`` MUST NOT include ``extract_citations``.

    Bound to the DebateAgent and ReviewWriterAgent stages. These work
    on textual review output and have no use for structured bibliography
    extraction, so the GROBID tool is intentionally absent.
    """
    skill = _SKILLS_BY_NAME["paper-review-write"]
    assert "extract_citations" not in skill["builtin_tools"], (
        f"Did NOT expect 'extract_citations' in paper-review-write.builtin_tools, "
        f"got {skill['builtin_tools']!r}"
    )


# ---------------------------------------------------------------------------
# Guards — unchanged skills
# ---------------------------------------------------------------------------


@pytest.mark.unit_db
def test_original_paper_review_skill_unchanged() -> None:
    """The original ``paper-review`` skill keeps ``builtin_tools == []``.

    Guard against accidental regression: the original is still referenced
    by legacy AgentConfig rows and should keep its empty tool set.
    """
    skill = _SKILLS_BY_NAME["paper-review"]
    assert skill["builtin_tools"] == [], (
        f"Original 'paper-review' builtin_tools changed: {skill['builtin_tools']!r}"
    )


@pytest.mark.unit_db
def test_solo_paper_review_skill_unchanged() -> None:
    """The standalone ``solo-paper-review`` skill keeps its full tool set.

    Guard against accidental regression: the Proposal Reviewer AgentConfig
    (line ~811 of scholarflow_skills.py) still references this skill and
    depends on all five tools.
    """
    skill = _SKILLS_BY_NAME["solo-paper-review"]
    assert skill["builtin_tools"] == [
        "search_papers",
        "extract_pdf_text",
        "extract_citations",
        "format_citation",
        "find_citation",
    ], (
        f"Standalone 'solo-paper-review' builtin_tools changed: {skill['builtin_tools']!r}"
    )
