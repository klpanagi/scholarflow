import asyncio

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState
from app.services.academic_apis import semantic_scholar, arxiv_api, crossref_api, openalex_api


def _extract_paper_title(full_text: str) -> str:
    import re

    text = full_text.strip()

    # Strip "PAPER / INPUT:" prefix injected by _build_stage_context
    paper_block = re.search(r"PAPER\s*/\s*INPUT:\s*\n(.+)", text, re.IGNORECASE | re.DOTALL)
    if paper_block:
        text = paper_block.group(1).strip()

    title_match = re.search(r"^Title[:\s]+([^\n]+)", text, re.IGNORECASE | re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()

    # Handle task_template format: "Paper:\n{content}\n\nOutput:"
    paper_match = re.search(r"Paper:\s*\n(.+?)(?:\n\n|\nOutput:)", text, re.IGNORECASE | re.DOTALL)
    if paper_match:
        inner = paper_match.group(1).strip()
        inner_title = re.search(r"^Title[:\s]+([^\n]+)", inner, re.IGNORECASE | re.MULTILINE)
        if inner_title:
            return inner_title.group(1).strip()
        first_line = inner.split("\n")[0].strip()
        if len(first_line) > 10:
            return first_line[:120]

    # Fallback: first substantial non-instruction line
    for line in text.split("\n"):
        line = line.strip()
        if (
            len(line) > 10
            and not line.lower().startswith(("you are", "search for", "find ", "output:", "paper:", "instruction"))
            and not line.startswith(("- ", "* ", "1.", "2.", "3."))
        ):
            return line[:120]

    return text[:120]


async def verify_paper_exists(title: str, doi: str | None = None) -> dict:
    import re
    
    if doi:
        try:
            result = await semantic_scholar.search(doi, limit=1)
            if result:
                return {"verified": True, "source": "semantic_scholar", "url": f"https://doi.org/{doi}", "title": result[0].title}
        except Exception:
            pass
    
    try:
        results = await semantic_scholar.search(title, limit=3)
        for r in results:
            title_lower = r.title.lower().strip()
            search_title_lower = title.lower().strip()
            if title_lower == search_title_lower or search_title_lower in title_lower or title_lower in search_title_lower:
                return {"verified": True, "source": "semantic_scholar", "url": getattr(r, "url", None), "title": r.title}
    except Exception:
        pass
    
    try:
        results = await openalex_api.search(title, limit=3)
        for r in results:
            title_lower = r.title.lower().strip()
            search_title_lower = title.lower().strip()
            if title_lower == search_title_lower or search_title_lower in title_lower or title_lower in search_title_lower:
                return {"verified": True, "source": "openalex", "url": getattr(r, "url", None), "title": r.title}
    except Exception:
        pass
    
    return {"verified": False, "source": None, "url": None, "title": title}


def _extract_search_queries(full_text: str, max_queries: int = 8) -> list[str]:
    import re

    primary = _extract_paper_title(full_text)
    queries = [primary]

    text = full_text.strip()
    paper_block = re.search(r"PAPER\s*/\s*INPUT:\s*\n(.+)", text, re.IGNORECASE | re.DOTALL)
    if paper_block:
        text = paper_block.group(1).strip()

    paper_match = re.search(r"Paper\s+to\s+review:\s*\n(.+?)(?:\n\n|\nCRITICAL|\nOutput:)", text, re.IGNORECASE | re.DOTALL)
    if paper_match:
        text = paper_match.group(1).strip()

    abstract = ""
    abstract_match = re.search(r"Abstract[:\s]+(.+?)(?:\n\n|\nFull Text:|\nKeywords:|\nScientific)", text, re.IGNORECASE | re.DOTALL)
    if abstract_match:
        abstract = abstract_match.group(1).strip()[:500]
        sentences = re.split(r"[.!]", abstract)
        if sentences and len(sentences[0].split()) >= 3:
            queries.append(sentences[0].strip()[:120])

    kw_match = re.search(r"(?:keywords?|key terms?|Auto Tags)[:\s]+(.+?)(?:\n|$)", text, re.IGNORECASE)
    if kw_match:
        queries.append(kw_match.group(1).strip()[:120])

    areas_match = re.search(r"Scientific Areas[:\s]+(.+?)(?:\n|$)", text, re.IGNORECASE)
    if areas_match:
        queries.append(areas_match.group(1).strip()[:120])

    seen = set()
    unique = []
    for q in queries:
        q_clean = q.lower().strip()
        if q_clean not in seen and len(q_clean) > 5:
            seen.add(q_clean)
            unique.append(q)
    return unique[:max_queries]


def _extract_tool_names(full_text: str) -> list[str]:
    """Extract specific tool/framework names from message content.

    Looks for:
    1. Explicit tool names in instructions (e.g., 'Search for RisQFLan')
    2. Capitalized names that look like tool names (e.g., 'CAL', 'PyCascades')
    3. Tool names in backticks or quotes
    """
    import re

    NON_TOOLS = {
        'The', 'This', 'That', 'What', 'When', 'Where', 'How', 'Why',
        'You', 'Your', 'Output', 'Input', 'Paper', 'Title', 'Authors',
        'Abstract', 'Keywords', 'Search', 'Find', 'List', 'For',
        'CRITICAL', 'INSTRUCTIONS', 'STEP', 'NOTE', 'IMPORTANT',
        'DSL', 'STPA', 'DOI', 'URL', 'PDF', 'XML', 'JSON',
        'EACH', 'DSLs', 'BROADER', 'COMPETING', 'TOOLS', 'APPROACHES',
        'DOMAIN', 'CONCEPTS', 'RELATED', 'WORK', 'SPECIFICALLY',
        'USED', 'FOUND', 'ASSESSMENT', 'GAPS', 'OUTPUT',
    }

    tool_names = []

    search_patterns = [
        r"search\s+for\s+['\"]?([A-Z][A-Za-z0-9]+)['\"]?",
        r"Search\s+for\s+['\"]?([A-Z][A-Za-z0-9]+)['\"]?",
        r"specifically[.\s]+['\"]?([A-Z][A-Za-z0-9]+)['\"]?",
    ]
    for pattern in search_patterns:
        matches = re.findall(pattern, full_text)
        tool_names.extend([t for t in matches if t not in NON_TOOLS and len(t) > 2])

    quoted_patterns = [
        r"['\"]([A-Z][A-Za-z0-9]+)['\"]",
        r"`([A-Z][A-Za-z0-9]+)`",
    ]
    for pattern in quoted_patterns:
        matches = re.findall(pattern, full_text)
        tool_names.extend([t for t in matches if t not in NON_TOOLS and len(t) > 2])

    tool_context = re.findall(
        r"(?:tool|framework|system|platform|language|DSL|library|package|approach|method|model|notation)[s]?\s+(?:called|named|is|like|such as|including|e\.g\.)\s+([A-Z][A-Za-z0-9]+)",
        full_text
    )
    tool_names.extend([t for t in tool_context if t not in NON_TOOLS and len(t) > 2])

    seen = set()
    unique = []
    for name in tool_names:
        name_lower = name.lower()
        if name_lower not in seen and len(name) > 2:
            seen.add(name_lower)
            unique.append(name)

    return unique


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

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def search_papers(state: AgentState) -> AgentState:
            message_content = state["messages"][-1].content
            queries = _extract_search_queries(message_content)
            tool_names = _extract_tool_names(message_content)

            for tool_name in tool_names:
                if tool_name.lower() not in [q.lower() for q in queries]:
                    queries.append(tool_name)

            all_results = []
            seen_titles = set()

            async def _search_one_source(q: str, source_name: str):
                try:
                    if source_name == "s2":
                        return await semantic_scholar.search(q, limit=5)
                    elif source_name == "arxiv":
                        return await arxiv_api.search(q, max_results=5)
                    elif source_name == "crossref":
                        return await crossref_api.search(q, rows=3)
                    elif source_name == "openalex":
                        return await openalex_api.search(q, limit=5)
                except Exception:
                    pass
                return []

            for q in queries:
                results_by_source = await asyncio.gather(
                    _search_one_source(q, "s2"),
                    _search_one_source(q, "arxiv"),
                    _search_one_source(q, "crossref"),
                    _search_one_source(q, "openalex"),
                )
                for source_results in results_by_source:
                    for r in source_results:
                        title_lower = r.title.lower() if hasattr(r, 'title') else r.get('title', '').lower()
                        if title_lower and title_lower not in seen_titles:
                            seen_titles.add(title_lower)
                            all_results.append(r)

            state["context"]["search_results"] = all_results[:20]
            state["context"]["search_queries"] = queries
            return state

        async def synthesize(state: AgentState) -> AgentState:
            results = state["context"].get("search_results", [])
            queries_used = state["context"].get("search_queries", [])
            if not results:
                state["output"] = "No papers found for your query."
                return state

            async def _verify(r):
                if isinstance(r, dict):
                    title = r.get("title", "Untitled")
                    doi = r.get("doi")
                else:
                    title = getattr(r, "title", "Untitled")
                    doi = getattr(r, "doi", None)
                verification = await verify_paper_exists(title, doi)
                return r, verification

            verification_tasks = [_verify(r) for r in results[:15]]
            verification_results = await asyncio.gather(*verification_tasks)

            verified_results = []
            for r, verification in verification_results:
                if verification["verified"]:
                    if isinstance(r, dict):
                        r["verified"] = True
                        r["verification_source"] = verification["source"]
                    else:
                        r = {
                            "title": getattr(r, "title", "Untitled"),
                            "authors": getattr(r, "authors", []) or [],
                            "year": getattr(r, "year", None),
                            "source": getattr(r, "source", ""),
                            "citation_count": getattr(r, "citation_count", None),
                            "abstract": getattr(r, "abstract", None),
                            "doi": getattr(r, "doi", None),
                            "verified": True,
                            "verification_source": verification["source"],
                        }
                    verified_results.append(r)

            lines = []
            for r in verified_results:
                if isinstance(r, dict):
                    title = r.get("title", "Untitled")
                    authors = r.get("authors", []) or []
                    year = r.get("year")
                    source = r.get("source", "")
                    citations = r.get("citation_count")
                    abstract = r.get("abstract")
                    verified = r.get("verified", False)
                else:
                    title = getattr(r, "title", "Untitled")
                    authors = getattr(r, "authors", []) or []
                    year = getattr(r, "year", None)
                    source = getattr(r, "source", "")
                    citations = getattr(r, "citation_count", None)
                    abstract = getattr(r, "abstract", None)
                    verified = False

                authors_str = ", ".join(authors[:3]) + ("..." if len(authors) > 3 else "")
                verified_tag = " ✓" if verified else ""
                line = (
                    f"- **{title}**{verified_tag} ({year or 'N/A'})\n"
                    f"  Authors: {authors_str}\n"
                    f"  Source: {source} | Citations: {citations or 'N/A'}"
                )
                if abstract:
                    line += f"\n  {abstract[:200]}..."
                lines.append(line)

            results_text = "\n\n".join(lines)
            queries_text = ", ".join(queries_used)

            synthesis_prompt = (
                f"Search queries used: {queries_text}\n\n"
                f"Found {len(verified_results)} verified papers (out of {len(results)} total). "
                f"Papers marked with ✓ have been verified in academic databases. "
                f"ONLY cite papers marked with ✓ in your review.\n\n"
                f"Results:\n{results_text}"
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
