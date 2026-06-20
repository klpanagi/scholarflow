from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState
from app.tools.document_reader import read_document


class RevisionAgent(BaseAgent):
    name = "revision"
    description = "Interactively revise and improve workflow results with fact-checking"
    default_tools: list = [read_document]

    system_prompt = (
        "You are an expert academic editor specializing in revising review documents.\n\n"
        "YOUR ROLE: You help users revise and improve the REVIEW DOCUMENT produced by a workflow — "
        "NOT the original paper being reviewed. The workflow generates a review report with sections "
        "like methodology analysis, strengths/weaknesses, related work, etc. Your job is to help "
        "the user refine that review document itself.\n\n"
        "CONTEXT AVAILABLE TO YOU:\n"
        "- The original paper content (metadata, abstract, full text)\n"
        "- All workflow stage outputs (search results, review stages, refined review)\n"
        "- The user's revision requests and conversation history\n\n"
        "CAPABILITIES:\n"
        "- Rewriting sections for clarity, tone, and academic rigor\n"
        "- Expanding or condensing content as requested\n"
        "- Restructuring arguments and improving logical flow\n"
        "- Adding more citations to the related work section\n"
        "- Strengthening the strengths/weaknesses analysis\n"
        "- Improving the methodology critique\n"
        "- Fact-checking claims against the paper content and available literature\n"
        "- Maintaining consistency across the document\n\n"
        "WHEN REVISING THE REVIEW:\n"
        "1. Preserve the original review structure unless explicitly asked to change it\n"
        "2. Maintain citation consistency and proper attribution\n"
        "3. Flag any claims you cannot verify\n"
        "4. Show what changed when making significant modifications\n"
        "5. Ask clarifying questions if the revision request is ambiguous\n"
        "6. Always work with the FULL document — produce the complete revised review\n\n"
        "IMPORTANT: You are revising the REVIEW, not the PAPER. If the user asks about "
        "revising the actual paper (e.g., 'improve my methodology'), redirect them to "
        "explain that you can help improve the REVIEW'S analysis of their methodology, "
        "not the paper itself.\n\n"
        "TOOLS AVAILABLE: read_document(file_path: str) - reads a local file (PDF, DOCX, "
        "MD, TXT, etc.). Use this to fetch uploaded files when the user references them. "
        "Example: if the user says 'cite section 4 of the PDF I uploaded', use this tool "
        "to fetch the file first.\n\n"
        "KNOWN LIMITATION: The streaming chat path may not bind tools to the LLM, so "
        "tool calls may not execute end-to-end. If the user references an uploaded file, "
        "ask them to paste the relevant excerpt directly into the chat so you can revise "
        "the document with the exact source content."
    )

    def __init__(self, llm, strategy_name="direct", tools=None, system_prompt=None):
        super().__init__(llm, strategy_name, tools=[], system_prompt=system_prompt)
        self.tools = tools if tools is not None else self.default_tools

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def understand_revision(state: AgentState) -> AgentState:
            workflow_result = state["context"].get("workflow_result", "")
            user_request = state["messages"][-1].content if state["messages"] else ""

            analysis_prompt = (
                f"Analyze this revision request for the following document.\n\n"
                f"DOCUMENT:\n{workflow_result[:3000]}\n\n"
                f"REVISION REQUEST: {user_request}\n\n"
                f"Determine:\n"
                f"1. Which section(s) need revision\n"
                f"2. What type of revision (rewrite, expand, condense, restructure, fact-check, add citations)\n"
                f"3. Any specific constraints or requirements\n"
                f"4. Whether fact-checking is needed (are there claims to verify?)\n"
            )

            response = await self.strategy.execute(
                self.llm,
                [HumanMessage(content=analysis_prompt)],
                self.system_prompt,
            )
            state["context"]["revision_analysis"] = response.content
            usage = getattr(response, "additional_kwargs", {}).get("usage")
            if usage:
                state["context"]["_usage"] = usage
            return state

        async def apply_revision(state: AgentState) -> AgentState:
            workflow_result = state["context"].get("workflow_result", "")
            revision_analysis = state["context"].get("revision_analysis", "")
            user_request = state["messages"][-1].content if state["messages"] else ""
            attached_files = state["context"].get("attached_files") or []

            attached_files_block = ""
            if attached_files:
                attached_files_block = (
                    f"\n\nATTACHED FILES (use read_document to fetch):\n"
                    + "\n".join(
                        f"- {f.get('file_name', 'unknown')}: {f.get('file_key', 'unknown')}"
                        for f in attached_files
                    )
                    + "\nUse the read_document tool with the local file path to access the file content.\n"
                )

            revision_prompt = (
                f"Based on the analysis:\n{revision_analysis}\n\n"
                f"ORIGINAL DOCUMENT:\n{workflow_result}\n\n"
                f"USER REQUEST: {user_request}\n\n"
                f"Apply the requested revision. Produce the complete revised document "
                f"with all changes integrated. Maintain the original structure unless "
                f"the request specifically asks for restructuring."
                f"{attached_files_block}"
            )

            response = await self.strategy.execute(
                self.llm,
                state["messages"] + [HumanMessage(content=revision_prompt)],
                self.system_prompt,
            )
            state["output"] = response.content
            state["context"]["revised_document"] = response.content
            usage = getattr(response, "additional_kwargs", {}).get("usage")
            if usage:
                existing = state["context"].get("_usage", {})
                if existing:
                    usage = {
                        "input_tokens": usage.get("input_tokens", 0) + existing.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0) + existing.get("output_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0) + existing.get("total_tokens", 0),
                    }
                state["context"]["_usage"] = usage
            return state

        graph.add_node("understand_revision", understand_revision)
        graph.add_node("apply_revision", apply_revision)

        graph.set_entry_point("understand_revision")
        graph.add_edge("understand_revision", "apply_revision")
        graph.add_edge("apply_revision", END)

        return graph
