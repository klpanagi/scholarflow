from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState
from app.utils.pdf_model_support import extract_text_from_message_content


class WritingAgent(BaseAgent):
    name = "writing"
    description = "Assist with academic paper writing, structure, and formatting"
    system_prompt = (
        "You are an expert academic writing assistant. You help researchers "
        "write clear, well-structured academic papers.\n\n"
        "Your capabilities include:\n"
        "- Drafting sections (abstract, introduction, methodology, results, discussion)\n"
        "- Improving clarity and academic tone\n"
        "- Suggesting better phrasing and transitions\n"
        "- Formatting references and citations\n"
        "- Ensuring logical flow and argumentation\n\n"
        "Always maintain academic integrity and proper attribution."
    )

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def understand_task(state: AgentState) -> AgentState:
            messages = state["messages"]
            user_msg = extract_text_from_message_content(messages[-1].content) if messages else ""

            task_prompt = (
                f"Analyze this writing request and determine:\n"
                f"1. What type of writing task (draft, edit, restructure, etc.)\n"
                f"2. Which section(s) are involved\n"
                f"3. Any specific requirements\n\n"
                f"Request: {user_msg}"
            )

            response = await self.strategy.execute(
                self.llm,
                messages[:-1] + [HumanMessage(content=task_prompt)],
                self.system_prompt,
            )
            state["context"]["task_analysis"] = response.content
            # Capture token usage from strategy
            usage = getattr(response, "additional_kwargs", {}).get("usage")
            if usage:
                state["context"]["_usage"] = usage
            return state

        async def generate_content(state: AgentState) -> AgentState:
            task_analysis = state["context"].get("task_analysis", "")
            original_messages = state["messages"]

            writing_prompt = (
                f"Based on the task analysis:\n{task_analysis}\n\n"
                f"Generate the requested academic content. "
                f"Use proper academic style, clear structure, and precise language."
            )

            response = await self.strategy.execute(
                self.llm,
                original_messages + [HumanMessage(content=writing_prompt)],
                self.system_prompt,
            )
            state["output"] = response.content
            # Capture token usage from strategy (accumulate with prior calls)
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

        graph.add_node("understand_task", understand_task)
        graph.add_node("generate_content", generate_content)

        graph.set_entry_point("understand_task")
        graph.add_edge("understand_task", "generate_content")
        graph.add_edge("generate_content", END)

        return graph
