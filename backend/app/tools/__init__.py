from app.tools.search import search_papers, search_web
from app.tools.pdf import extract_pdf_text, extract_citations
from app.tools.citation import format_citation, find_citation
from app.tools.document_reader import read_document

__all__ = [
    "search_papers",
    "search_web",
    "extract_pdf_text",
    "extract_citations",
    "format_citation",
    "find_citation",
    "read_document",
]

TOOL_REGISTRY: dict[str, object] = {
    "search_papers": search_papers,
    "search_web": search_web,
    "extract_pdf_text": extract_pdf_text,
    "extract_citations": extract_citations,
    "format_citation": format_citation,
    "find_citation": find_citation,
    "read_document": read_document,
}


def get_tools_by_names(tool_names: list[str]) -> list[object]:
    tools = []
    for name in tool_names:
        tool_fn = TOOL_REGISTRY.get(name)
        if tool_fn:
            tools.append(tool_fn)
    return tools
