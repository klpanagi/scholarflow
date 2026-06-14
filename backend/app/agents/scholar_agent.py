from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState
from app.services.academic_apis import semantic_scholar, arxiv_api, crossref_api


def _extract_search_query(full_text: str, max_chars: int = 80) -> str:
    import re

    text = full_text.strip()

    title_match = re.search(r"^Title[:\s]+([^\n]+)", text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
        abstract_match = re.search(r"Abstract[:\s]+([^\n]+)", text, re.IGNORECASE)
        if abstract_match:
            abstract = abstract_match.group(1).strip()[:60]
            return f"{title[:60]}. {abstract}".strip()
        return title[:max_chars]

    short_input = re.search(
        r"(?:briefly |about |related to |for )?([^.!?\n]{10,100})",
        text,
        re.IGNORECASE,
    )
    if short_input:
        return short_input.group(1).strip()

    return text[:max_chars]


class ScholarAgent(BaseAgent):
    name = "scholar"
    description = "Search and discover academic papers across multiple sources"
    system_prompt = (
        "You are a scholarly research assistant. Your role is to help users "
        "find relevant academic papers, understand research trends, and discover "
        "new publications in their field of interest.\n\n"
        "When searching for papers:\n"
        "- Use precise, domain-specific terminology\n"
        "- Consider synonyms and related concepts\n"
        "- Prioritize recent publications unless told otherwise\n"
        "- Provide context about why papers are relevant\n\n"
        "Always cite sources with title, authors, year, and venue when available."
    )

    def _get_tool(self, name: str):
        for t in self.tools:
            if getattr(t, "name", None) == name:
                return t
        return None

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def search_papers(state: AgentState) -> AgentState:
            short_query = _extract_search_query(state["messages"][-1].content)

            results = []

            search_tool = self._get_tool("search_papers")
            if search_tool:
                tool_result = await search_tool.ainvoke({"query": short_query, "limit": 5})
                results = tool_result if isinstance(tool_result, list) else []
            else:
                s2_results = await semantic_scholar.search(short_query, limit=3)
                results.extend(s2_results)

                arxiv_results = await arxiv_api.search(short_query, max_results=3)
                results.extend(arxiv_results)

                crossref_results = await crossref_api.search(short_query, rows=3)
                results.extend(crossref_results)

            state["context"]["search_results"] = results[:5]
            return state

        async def synthesize(state: AgentState) -> AgentState:
            results = state["context"].get("search_results", [])
            if not results:
                state["output"] = "No papers found for your query."
                return state

            lines = []
            for r in results[:10]:
                if isinstance(r, dict):
                    title = r.get("title", "Untitled")
                    authors = r.get("authors", []) or []
                    year = r.get("year")
                    source = r.get("source", "")
                    citations = r.get("citation_count")
                    abstract = r.get("abstract")
                else:
                    title = getattr(r, "title", "Untitled")
                    authors = getattr(r, "authors", []) or []
                    year = getattr(r, "year", None)
                    source = getattr(r, "source", "")
                    citations = getattr(r, "citation_count", None)
                    abstract = getattr(r, "abstract", None)

                authors_str = ", ".join(authors[:3]) + ("..." if len(authors) > 3 else "")
                line = (
                    f"- **{title}** ({year or 'N/A'})\n"
                    f"  Authors: {authors_str}\n"
                    f"  Source: {source} | Citations: {citations or 'N/A'}"
                )
                if abstract:
                    line += f"\n  {abstract[:200]}..."
                lines.append(line)

            results_text = "\n\n".join(lines)

            synthesis_prompt = (
                f"Based on these search results, provide a helpful summary "
                f"for the user's query. Group by relevance and highlight "
                f"key findings.\n\nResults:\n{results_text}"
            )

            response = await self.strategy.execute(
                self.llm,
                state["messages"] + [HumanMessage(content=synthesis_prompt)],
                self.system_prompt,
            )
            state["output"] = response.content
            return state

        graph.add_node("search_papers", search_papers)
        graph.add_node("synthesize", synthesize)

        graph.set_entry_point("search_papers")
        graph.add_edge("search_papers", "synthesize")
        graph.add_edge("synthesize", END)

        return graph
