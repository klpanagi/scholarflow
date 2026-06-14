import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState


REVIEW_SYSTEM_PROMPT = """You are a rigorous academic paper reviewer. You follow a structured pipeline to produce comprehensive reviews.

Produce a single consolidated review that is thorough, evidence-based, and constructive. Never be dismissive.
"""


class PaperReviewAgent(BaseAgent):
    name = "paper-review"
    description = "Structured academic paper review pipeline producing a single consolidated review"
    system_prompt = REVIEW_SYSTEM_PROMPT

    def _get_tool(self, name: str):
        for t in self.tools:
            if getattr(t, "name", None) == name:
                return t
        return None

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        graph.add_node("intake", self._intake)
        graph.add_node("structural", self._structural_analysis)
        graph.add_node("claims", self._claim_extraction)
        graph.add_node("methodology", self._methodology_verification)
        graph.add_node("literature", self._literature_grounding)
        graph.add_node("adversarial", self._adversarial_red_team)
        graph.add_node("synthesis", self._synthesis)

        graph.set_entry_point("intake")
        
        graph.add_edge("intake", "structural")
        graph.add_edge("intake", "claims")
        graph.add_edge("intake", "methodology")
        
        graph.add_edge("claims", "literature")
        graph.add_edge("claims", "adversarial")
        graph.add_edge("methodology", "adversarial")

        graph.add_edge("structural", "synthesis")
        graph.add_edge("literature", "synthesis")
        graph.add_edge("adversarial", "synthesis")
        
        graph.add_edge("synthesis", END)

        return graph

    async def _intake(self, state: AgentState) -> AgentState:
        paper_content = state["context"].get("paper_content", "")
        if not paper_content:
            file_key = state["context"].get("file_key")
            if file_key:
                from app.services.minio_service import minio_service
                paper_content_bytes = minio_service.download_file(file_key)
                paper_content = paper_content_bytes.decode("utf-8", errors="replace")

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 0: INTAKE

Extract structured data: title, authors, abstract, paper type, key sections.

Paper content:
{paper_content[:5000]}"""),
        ]

        response = await self.llm.ainvoke(messages)
        state["context"]["intake"] = response.content
        state["context"]["paper_content"] = paper_content
        return state

    async def _structural_analysis(self, state: AgentState) -> AgentState:
        intake = state["context"].get("intake", "")
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 1: STRUCTURAL ANALYSIS

Evaluate IMRaD completeness, figure/table quality, references, writing quality. Score 1-10.

{intake[:2000]}"""),
        ]

        response = await self.llm.ainvoke(messages)
        state["context"]["structural"] = response.content
        return state

    async def _claim_extraction(self, state: AgentState) -> AgentState:
        intake = state["context"].get("intake", "")
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 2: CLAIM EXTRACTION

List the top 5 claims and their evidence strength (Strong/Moderate/Weak/Unsupported).

{intake[:2000]}"""),
        ]

        response = await self.llm.ainvoke(messages)
        state["context"]["claims"] = response.content
        return state

    async def _literature_grounding(self, state: AgentState) -> AgentState:
        claims = state["context"].get("claims", "")
        intake = state["context"].get("intake", "")

        paper_content = state["context"].get("paper_content", "")
        title_line = ""
        for line in paper_content.split("\n")[:20]:
            if len(line.strip()) > 10:
                title_line = line.strip()[:80]
                break

        search_results = ""
        search_tool = self._get_tool("search_papers")
        if title_line:
            try:
                if search_tool:
                    result = await search_tool.ainvoke({"query": title_line, "limit": 3})
                else:
                    from app.tools.search import search_papers
                    result = await search_papers.ainvoke({"query": title_line, "limit": 3})
                search_results = str(result)[:2000]
            except Exception:
                search_results = "Search unavailable"

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 3: LITERATURE GROUNDING

Assess literature coverage, baselines, novelty. Are key citations missing?

Claims: {claims[:1500]}
Search: {search_results}"""),
        ]

        response = await self.llm.ainvoke(messages)
        state["context"]["literature"] = response.content
        return state

    async def _methodology_verification(self, state: AgentState) -> AgentState:
        intake = state["context"].get("intake", "")
        claims = state["context"].get("claims", "")

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 4: METHODOLOGY VERIFICATION

Evaluate statistical rigor, reproducibility, experimental design, threats to validity.

Intake: {intake[:1500]}
Claims: {claims[:1500]}"""),
        ]

        response = await self.llm.ainvoke(messages)
        state["context"]["methodology"] = response.content
        return state

    async def _adversarial_red_team(self, state: AgentState) -> AgentState:
        claims = state["context"].get("claims", "")
        methodology = state["context"].get("methodology", "")

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Stage 5: ADVERSARIAL RED TEAM

Breaker: logical flaws. Butcher: missing experiments. Collector: novelty threats.

Claims: {claims[:1500]}
Methodology: {methodology[:1500]}"""),
        ]

        response = await self.llm.ainvoke(messages)
        state["context"]["adversarial"] = response.content
        return state

    async def _synthesis(self, state: AgentState) -> AgentState:
        intake = state["context"].get("intake", "")
        structural = state["context"].get("structural", "")
        claims = state["context"].get("claims", "")
        literature = state["context"].get("literature", "")
        methodology = state["context"].get("methodology", "")
        adversarial = state["context"].get("adversarial", "")

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""SYNTHESIS

Produce a single consolidated review of the paper that synthesizes the prior stages into actionable feedback for the authors.

Inputs:
- {intake[:1000]}
- {structural[:1000]}
- {claims[:1000]}
- {literature[:1000]}
- {methodology[:1000]}
- {adversarial[:1000]}"""),
        ]

        response = await self.llm.ainvoke(messages)
        state["output"] = response.content
        state["metadata"]["stages_completed"] = [
            "intake", "structural", "claims", "literature",
            "methodology", "adversarial", "synthesis",
        ]
        return state
