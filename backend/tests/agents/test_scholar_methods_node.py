"""Tests for the ScholarAgent.evaluate_methods node (Task 9).

The methods node reads context["deduplicated_results"], calls the LLM once per
top-15 paper (by final_rank) to extract a methodology row, and writes
context["methodology_table"] = list[MethodologyEntry].

Tests:
1. test_methods_node_extracts_from_abstracts — LLM returns valid JSON, 3 papers → 3 entries
2. test_methods_node_handles_invalid_json — LLM returns malformed JSON → entry with confidence="low"
3. test_methods_node_caps_at_15 — 20 papers → LLM called exactly 15 times, 15 entries
4. test_methods_node_skips_papers_without_abstract — 5 papers, 2 missing abstract → 3 entries
"""
from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage

from app.agents.base import AgentState
from app.agents.dossier import MethodologyEntry
from app.agents.scholar_agent import ScholarAgent


def _make_state(context: dict | None = None) -> AgentState:
    """Build a minimal AgentState. No messages required for the methods node."""
    return AgentState(
        messages=[],
        context=context or {},
        output=None,
        metadata={},
    )


def _make_paper(
    paper_id: str,
    *,
    title: str = "Untitled",
    abstract: str | None = "Sample abstract text.",
    final_rank: int = 0,
) -> dict:
    """Build a paper dict matching the deduplicated_results shape."""
    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "doi": None,
        "arxiv_id": None,
        "authors": [],
        "year": 2020,
        "venue": None,
        "citation_count": 0,
        "source": "semantic_scholar",
        "url": None,
        "matched_in": ["title"],
        "merged_sources": ["semantic_scholar"],
        "final_rank": final_rank,
    }


def _set_llm_responses(mock_llm, payloads: list[str]) -> None:
    """Configure mock_llm.ainvoke to return successive AIMessage responses.

    Each entry in `payloads` is the content of one AIMessage. The mock will
    raise StopIteration if called more times than entries provided — tests
    must size the list to the expected call count.
    """
    responses = [AIMessage(content=p) for p in payloads]
    mock_llm.ainvoke.side_effect = responses


class TestMethodsNodeExtractsFromAbstracts:
    @pytest.mark.asyncio
    async def test_methods_node_extracts_from_abstracts(self, mock_llm):
        """3 papers, LLM returns valid JSON for each → 3 MethodologyEntry rows."""
        agent = ScholarAgent(llm=mock_llm)
        papers = [
            _make_paper("p1", title="Transformer", abstract="We propose the Transformer model.", final_rank=0),
            _make_paper("p2", title="BERT", abstract="We introduce BERT for language understanding.", final_rank=1),
            _make_paper("p3", title="GPT-3", abstract="We scale GPT-3 to 175B parameters.", final_rank=2),
        ]
        state = _make_state(context={"deduplicated_results": papers})

        _set_llm_responses(
            mock_llm,
            [
                json.dumps({
                    "method_name": "Transformer",
                    "dataset": "WMT 2014 EN-DE",
                    "metrics": ["BLEU"],
                    "baseline_methods": ["LSTM"],
                    "result": "28.4 BLEU",
                    "confidence": "high",
                }),
                json.dumps({
                    "method_name": "BERT",
                    "dataset": "SQuAD 1.1",
                    "metrics": ["F1", "EM"],
                    "baseline_methods": ["ELMo"],
                    "result": "93.2 F1",
                    "confidence": "high",
                }),
                json.dumps({
                    "method_name": "GPT-3",
                    "dataset": "SuperGLUE",
                    "metrics": ["accuracy"],
                    "baseline_methods": ["BERT", "RoBERTa"],
                    "result": "71.8% accuracy",
                    "confidence": "medium",
                }),
            ],
        )

        await agent.evaluate_methods(state)

        table = state["context"].get("methodology_table", [])
        assert len(table) == 3, f"Expected 3 entries, got {len(table)}"
        assert all(isinstance(m, MethodologyEntry) for m in table), (
            f"Expected MethodologyEntry instances, got {[type(m).__name__ for m in table]}"
        )

        # Order preserved
        assert table[0].paper_id == "p1"
        assert table[0].method_name == "Transformer"
        assert table[0].dataset == "WMT 2014 EN-DE"
        assert table[0].metrics == ["BLEU"]
        assert table[0].baseline_methods == ["LSTM"]
        assert table[0].result == "28.4 BLEU"
        assert table[0].confidence == "high"

        assert table[1].paper_id == "p2"
        assert table[1].method_name == "BERT"
        assert table[1].confidence == "high"

        assert table[2].paper_id == "p3"
        assert table[2].method_name == "GPT-3"
        assert table[2].confidence == "medium"


class TestMethodsNodeHandlesInvalidJson:
    @pytest.mark.asyncio
    async def test_methods_node_handles_invalid_json(self, mock_llm):
        """LLM returns malformed output → 1 MethodologyEntry with confidence='low'."""
        agent = ScholarAgent(llm=mock_llm)
        papers = [
            _make_paper("p1", title="Bad JSON paper", abstract="Some abstract text here."),
        ]
        state = _make_state(context={"deduplicated_results": papers})

        # No recoverable JSON object at all
        _set_llm_responses(
            mock_llm,
            ["This response contains no JSON at all, just prose about the paper."],
        )

        await agent.evaluate_methods(state)

        table = state["context"].get("methodology_table", [])
        assert len(table) == 1, f"Expected 1 entry (low-confidence fallback), got {len(table)}"
        assert isinstance(table[0], MethodologyEntry)
        assert table[0].paper_id == "p1"
        assert table[0].confidence == "low"


class TestMethodsNodeCapsAt15:
    @pytest.mark.asyncio
    async def test_methods_node_caps_at_15(self, mock_llm):
        """20 papers → LLM called exactly 15 times → 15 MethodologyEntry rows."""
        agent = ScholarAgent(llm=mock_llm)
        papers = [
            _make_paper(
                f"p{i}",
                title=f"Paper {i}",
                abstract=f"Abstract for paper {i} with enough content to be processed.",
                final_rank=i,
            )
            for i in range(20)
        ]
        state = _make_state(context={"deduplicated_results": papers})

        # Provide exactly 15 valid JSON responses
        responses = []
        for i in range(15):
            responses.append(json.dumps({
                "method_name": f"Method{i}",
                "dataset": f"Dataset{i}",
                "metrics": ["accuracy"],
                "baseline_methods": ["Baseline0"],
                "result": f"{90 + i}% accuracy",
                "confidence": "high",
            }))
        _set_llm_responses(mock_llm, responses)

        await agent.evaluate_methods(state)

        # LLM called exactly 15 times
        assert mock_llm.ainvoke.call_count == 15, (
            f"LLM should be called exactly 15 times, got {mock_llm.ainvoke.call_count}"
        )

        # 15 entries written
        table = state["context"].get("methodology_table", [])
        assert len(table) == 15, f"Expected 15 entries, got {len(table)}"

        # First 15 papers processed (by final_rank order = insertion order here)
        assert table[0].paper_id == "p0"
        assert table[14].paper_id == "p14"


class TestMethodsNodeSkipsPapersWithoutAbstract:
    @pytest.mark.asyncio
    async def test_methods_node_skips_papers_without_abstract(self, mock_llm):
        """5 papers, 2 without abstract → LLM called 3 times → 3 MethodologyEntry rows."""
        agent = ScholarAgent(llm=mock_llm)
        papers = [
            _make_paper("p1", title="Paper 1", abstract="Abstract 1.", final_rank=0),
            _make_paper("p2", title="Paper 2", abstract=None, final_rank=1),  # skipped
            _make_paper("p3", title="Paper 3", abstract="Abstract 3.", final_rank=2),
            _make_paper("p4", title="Paper 4", abstract="", final_rank=3),  # empty → skipped
            _make_paper("p5", title="Paper 5", abstract="Abstract 5.", final_rank=4),
        ]
        state = _make_state(context={"deduplicated_results": papers})

        # Provide 3 valid JSON responses (one per paper-with-abstract)
        responses = [
            json.dumps({
                "method_name": "Method1",
                "dataset": "D1",
                "metrics": ["m1"],
                "baseline_methods": ["b1"],
                "result": "r1",
                "confidence": "high",
            }),
            json.dumps({
                "method_name": "Method3",
                "dataset": "D3",
                "metrics": ["m3"],
                "baseline_methods": ["b3"],
                "result": "r3",
                "confidence": "high",
            }),
            json.dumps({
                "method_name": "Method5",
                "dataset": "D5",
                "metrics": ["m5"],
                "baseline_methods": ["b5"],
                "result": "r5",
                "confidence": "high",
            }),
        ]
        _set_llm_responses(mock_llm, responses)

        await agent.evaluate_methods(state)

        # LLM called exactly 3 times (no call for p2 or p4)
        assert mock_llm.ainvoke.call_count == 3, (
            f"LLM should be called 3 times (papers with abstract), "
            f"got {mock_llm.ainvoke.call_count}"
        )

        table = state["context"].get("methodology_table", [])
        assert len(table) == 3, f"Expected 3 entries, got {len(table)}"
        ids = [m.paper_id for m in table]
        assert ids == ["p1", "p3", "p5"], (
            f"Expected paper_ids [p1, p3, p5], got {ids}"
        )
