from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from app.agents.base import BaseAgent, AgentState
from app.services.search_service import search_service
from app.services.academic_apis import semantic_scholar, openalex_api
from app.agents.search_agent import _extract_paper_title
from app.utils.pdf_model_support import extract_text_from_message_content


class RecommendationAgent(BaseAgent):
    name = "recommendation"
    description = "Recommend relevant papers based on user interests and reading history"
    system_prompt = (
        "You are a research paper recommendation system. You help researchers "
        "discover papers relevant to their interests and current work.\n\n"
        "Consider:\n"
        "- Research domain and sub-topics\n"
        "- Methodological preferences\n"
        "- Recency vs foundational works\n"
        "- Cross-disciplinary connections\n"
        "- Citation networks\n\n"
        "Explain why each recommendation is relevant."
    )

    def _get_tool(self, name: str):
        for t in self.tools:
            if getattr(t, "name", None) == name:
                return t
        return None

    def build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        async def analyze_preferences(state: AgentState) -> AgentState:
            messages = state["messages"]
            user_msg = extract_text_from_message_content(messages[-1].content) if messages else ""

            pref_prompt = (
                f"Analyze the user's research interests and preferences:\n\n"
                f"{user_msg}\n\n"
                f"Extract: topics, keywords, preferred methodologies, "
                f"recent interests, and what they're looking for."
            )

            response = await self.strategy.execute(
                self.llm,
                messages[:-1] + [HumanMessage(content=pref_prompt)],
                self.system_prompt,
            )
            state["context"]["preferences"] = response.content
            # Capture token usage from strategy
            usage = getattr(response, "additional_kwargs", {}).get("usage")
            if usage:
                state["context"]["_usage"] = usage
            return state

        async def find_recommendations(state: AgentState) -> AgentState:
            preferences = state["context"].get("preferences", "")
            original_query = extract_text_from_message_content(state["messages"][-1].content)
            short_query = _extract_paper_title(original_query)

            search_tool = self._get_tool("search_papers")
            if search_tool:
                tool_result = await search_tool.ainvoke({"query": short_query, "limit": 10})
                state["context"]["vector_results"] = tool_result if isinstance(tool_result, list) else []
                state["context"]["api_results"] = []
            else:
                vector_results = await search_service.search(
                    query=short_query,
                    index="papers",
                    limit=10,
                )
                state["context"]["vector_results"] = vector_results

                s2_results = await semantic_scholar.search(short_query, limit=5)
                oa_results = await openalex_api.search(short_query, limit=5)
                seen = {r.title.lower() for r in s2_results}
                combined_api = list(s2_results)
                for r in oa_results:
                    if r.title.lower() not in seen:
                        seen.add(r.title.lower())
                        combined_api.append(r)
                state["context"]["api_results"] = combined_api

            return state

        async def rank_and_explain(state: AgentState) -> AgentState:
            vector_results = state["context"].get("vector_results", [])
            api_results = state["context"].get("api_results", [])
            preferences = state["context"].get("preferences", "")

            combined = []
            for r in vector_results:
                if isinstance(r, dict):
                    combined.append(f"- {r.get('title', 'Unknown')} (from library)")
                else:
                    combined.append(f"- {getattr(r, 'title', 'Unknown')} (from library)")
            for r in api_results:
                combined.append(f"- {r.title} ({r.year or 'N/A'}, {r.source})")

            rank_prompt = (
                f"Given the user preferences:\n{preferences}\n\n"
                f"And these candidate papers:\n{''.join(combined[:20])}\n\n"
                f"Select the top 5-10 most relevant papers and explain "
                f"why each is recommended."
            )

            response = await self.strategy.execute(
                self.llm,
                state["messages"] + [HumanMessage(content=rank_prompt)],
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

        graph.add_node("analyze_preferences", analyze_preferences)
        graph.add_node("find_recommendations", find_recommendations)
        graph.add_node("rank_and_explain", rank_and_explain)

        graph.set_entry_point("analyze_preferences")
        graph.add_edge("analyze_preferences", "find_recommendations")
        graph.add_edge("find_recommendations", "rank_and_explain")
        graph.add_edge("rank_and_explain", END)

        return graph
