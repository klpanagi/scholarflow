# CULT_SYSTEM

> **Authoritative reference for the ScholarFlow CULT system.**
>
> Replaces the now-obsolete `CULT_SYSTEM_ANALYSIS.md` (2024-era analysis of a 4-role, 15-skill, 4-workflow subset). The current implementation spans 9 roles, 10 runtime agents, 3 variants, 4 strategies, 10 seed skills, 14 seeded + default agent configs, 16 workflow definitions, and a streaming progress pipeline. This document is the source of truth — if code and this document disagree, update the document.

---

## Table of contents

1. [What the CULT system is](#1-what-the-cult-system-is)
2. [Layered architecture](#2-layered-architecture)
3. [Domain model — enums, tables, relations](#3-domain-model--enums-tables-relations)
4. [Tools — the leaf capability layer](#4-tools--the-leaf-capability-layer)
5. [Skills — reusable tool bundles](#5-skills--reusable-tool-bundles)
6. [Strategies — execution patterns](#6-strategies--execution-patterns)
7. [Runtime agents — the 10 LangGraph graphs](#7-runtime-agents--the-10-langgraph-graphs)
8. [Agent registry and factory](#8-agent-registry-and-factory)
9. [Agent configurations — seed + defaults](#9-agent-configurations--seed--defaults)
10. [Workflows — multi-stage orchestrations](#10-workflows--multi-stage-orchestrations)
11. [Progress and streaming](#11-progress-and-streaming)
12. [HTTP API surface](#12-http-api-surface)
13. [Frontend — `/cult/*` routes](#13-frontend--cult-routes)
14. [Cancellation, persistence, observability](#14-cancellation-persistence-observability)
15. [File index](#15-file-index)

---

## 1. What the CULT system is

**CULT** is the orchestration layer that turns a user prompt into structured academic work. It is not a single agent — it is a stack:

```
                 ┌───────────────────────────────────────────────┐
                 │           Workflows (16 multi-stage)          │
                 │   search-related-work, review-paper, debate…  │
                 └──────────────────────────┬────────────────────┘
                                            │
                 ┌──────────────────────────▼────────────────────┐
                 │          Agent Configs (per-user)             │
                 │  model + strategy + skills + system prompt   │
                 └──────────────────────────┬────────────────────┘
                                            │
                 ┌──────────────────────────▼────────────────────┐
                 │             Strategies (4)                    │
                 │   direct · critique · reflection · eval-opt   │
                 └──────────────────────────┬────────────────────┘
                                            │
                 ┌──────────────────────────▼────────────────────┐
                 │         Runtime Agents (10 graphs)            │
                 │   search · writing · review · debate · …      │
                 └──────────────────────────┬────────────────────┘
                                            │
                 ┌──────────────────────────▼────────────────────┐
                 │       Skills (10 seed) + Tools (7 leaf)        │
                 │   search_papers, read_document, citation…     │
                 └───────────────────────────────────────────────┘
```

The system was designed around three forces:

- **Composability** — a user can mix any role, any strategy, any model, and any combination of skills without code changes.
- **Observability** — every node, tool call, and strategy iteration is published through a `ProgressManager` so the UI can stream real-time status.
- **Failover isolation** — per-source search failures, tool errors, and individual node errors never crash the pipeline; they are recorded in the run state and surfaced in metadata.

The runtime is built on **LangGraph state graphs**. Each agent defines a `StateGraph`, a `BaseAgent` orchestrator drives it via `astream_events(version="v2")`, and the result is wrapped (or not) by a strategy iteration loop.

---

## 2. Layered architecture

| Layer | Path | Purpose |
|------|------|---------|
| **Domain model** | `backend/app/models/` | SQLAlchemy entities, enums (`AgentRole`, `Strategy`, `AgentVariant`) |
| **Tools** | `backend/app/tools/` | 7 leaf capabilities (search, citation, extraction, document reading) |
| **Skills** | `backend/app/api/routes/skills.py` + `backend/app/services/skill_service.py` | Named bundles of tools + system-prompt fragments |
| **Strategies** | `backend/app/agents/strategies/` | Execution loops: direct, critique, reflection, evaluator-optimizer |
| **Agents** | `backend/app/agents/*_agent.py` + `base.py` | 10 LangGraph state graphs |
| **Factory** | `backend/app/agents/factory.py` | Two-level registry: `role → class \| (variant → class)` |
| **Seeds** | `backend/app/seeds/scholarflow_skills.py` | 10 skills + 7 agent configs seeded per user on first login |
| **API** | `backend/app/api/routes/{agents,skills,workflows,…}.py` | HTTP surface (FastAPI routers) |
| **Frontend** | `frontend/src/pages/{AgentsPage,SkillsPage,ChatPage}.tsx` | `/cult/agents`, `/cult/skills`, `/cult/chat` |

---

## 3. Domain model — enums, tables, relations

### 3.1 Enums

#### `AgentRole` (`backend/app/models/__init__.py:17-26`)

Nine roles. Every runtime agent maps to exactly one role.

| Value | Runtime agent | Notes |
|------|---------------|-------|
| `researcher` | `SearchAgent` | Multi-source literature search |
| `writer` | `WritingAgent` | Generic content generation |
| `reviewer` | `ReviewAgent` | Workflow-integrated review, consumes `research_dossier` |
| `recommender` | `RecommendationAgent` | Paper recommendations |
| `revision` | `RevisionAgent` | Revises review documents (not papers) |
| `manager` | `WritingAgent` | Project / task management (reuses writer) |
| `debater` | `SimpleDebateAgent` / `DebateAgent` / `DeepDebateAgent` | Variant-selected |
| `deep_reviewer` | `DeepReviewAgent` | 7-stage rubric-based review |
| `review_writer` | `ReviewWriterAgent` | Self-critique review with editor + author sections |

#### `Strategy` (4 values, unchanged from the 2024 analysis)

| Value | Behavior |
|------|----------|
| `direct` | One LLM call. No iteration. |
| `critique` | generate → critique → refine, repeated per iteration |
| `reflection` | generate → reflect, repeated per iteration |
| `evaluator_optimizer` | generate → evaluate (scored) → optimize, repeated per iteration |

#### `AgentVariant` (new since 2024)

Three values, used **only** by the `debater` role:

| Value | Agent | Cost |
|------|-------|------|
| `simple` | `SimpleDebateAgent` | 2 LLM calls, ~20K tokens |
| `standard` | `DebateAgent` | 3 LLM calls, ~30K tokens |
| `deep` | `DeepDebateAgent` | 3 LLM calls, ~40K tokens |

The `AgentConfig` model adds a nullable `variant` column. It is `None` for all non-debater configs and one of the three values for debater configs.

### 3.2 Tables (excerpt — full schema in `backend/app/models/`)

| Table | Purpose |
|------|---------|
| `agent_configs` | Per-user agent configuration: name, role, model, provider, strategy, variant, system_prompt, temperature, max_tokens, is_default |
| `skills` | Per-user (or public) named bundle: name, description, system_prompt, is_public, user_id |
| `agent_skills` | M2M association table: `agent_config_id ↔ skill_id` |
| `workflow_executions` | One row per workflow run, holds stages and final state |
| `workflow_events` | Append-only progress events for a workflow execution |
| `revision_sessions` / `revision_messages` | Revision chat history |
| `user_api_keys` | Fernet-encrypted per-user provider keys (OpenAI, Anthropic, OpenRouter, Semantic Scholar) |
| `assets` / `asset_chunks` | Uploaded papers (PDF, text) with extracted chunks |
| `chat_sessions` / `chat_messages` | Per-session chat with optional asset binding |

### 3.3 Relations

```
User 1───* AgentConfig *───* Skill (via agent_skills)
User 1───* Skill (own)        Skill *───* Tool (resolved by name at runtime)
User 1───* WorkflowExecution 1───* WorkflowEvent
User 1───* RevisionSession 1───* RevisionMessage
User 1───* Asset 1───* AssetChunk
User 1───* ChatSession 1───* ChatMessage
```

Skills are resolved by **name** at runtime. A skill stores tool names as strings; the agent's `get_tools_by_names(...)` resolves them against the singleton `BUILTIN_TOOLS` registry.

---

## 4. Tools — the leaf capability layer

Defined in `backend/app/tools/__init__.py` (33 lines). The registry is a frozen list of seven built-in tools, each implemented as a LangChain `@tool`-decorated function.

| Tool name | Purpose | Used by (skills) |
|-----------|---------|------------------|
| `search_papers` | Multi-source academic search (S2 / arXiv / CrossRef / OpenAlex) | `eu-horizon`, `academic-writing`, `paper-review`, `literature-review` |
| `search_web` | General web search | `eu-horizon`, `literature-review` |
| `extract_pdf_text` | Extract text from a PDF URL or local path | `paper-review`, `paper-review-analyze` |
| `extract_citations` | Parse references from a paper's full text | `paper-review`, `paper-review-analyze` |
| `format_citation` | Render a paper record in BibTeX / APA / MLA / Chicago | `academic-writing`, `paper-review`, `paper-review-analyze`, `paper-review-write`, `literature-review` |
| `find_citation` | Resolve a free-text citation to a paper record | `academic-writing`, `paper-review`, `paper-review-analyze`, `paper-review-write` |
| `read_document` | Read a text asset from the user's library (chunked) | `solo-paper-review`, `paper-review` |

`get_tools_by_names(names)` is the public resolution API. It returns a deduplicated list of tool objects; unknown names are silently dropped. The skills layer uses this to build the runtime tool set passed to the LLM.

`BUILTIN_TOOLS` (in `backend/app/api/routes/skills.py:28-36`) is a parallel dict used for the `/builtin-tools` discovery endpoint.

---

## 5. Skills — reusable tool bundles

Skills live in the database, not in code. They are created per-user (or marked public) and bound to agent configs through the M2M table.

### 5.1 Seed skills (`backend/app/seeds/scholarflow_skills.py:_SKILL_SEEDS`)

Ten skills are seeded for every new user on first login. Each has a name, description, system_prompt, and an explicit list of tool names.

| # | Skill name | Tools | Purpose |
|---|------------|-------|---------|
| 1 | `eu-horizon` | `search_web`, `search_papers` | EU/HE funding context (Horizon Europe, ERC) |
| 2 | `academic-writing` | `search_papers`, `format_citation`, `find_citation` | General academic prose and citation handling |
| 3 | `project-management` | — | Planning, milestones, Gantt-style reasoning |
| 4 | `solo-paper-review` | `read_document` | Single-paper review, user-library document access |
| 5 | `paper-review` | `extract_pdf_text`, `extract_citations`, `format_citation`, `find_citation`, `read_document` | Full review pipeline (extraction + citations) |
| 6 | `paper-review-analyze` | `extract_pdf_text`, `extract_citations`, `format_citation`, `find_citation` | Analysis stage only — no document reading |
| 7 | `paper-review-write` | `format_citation`, `find_citation` | Writing stage only — citation formatting |
| 8 | `literature-review` | `search_papers`, `search_web`, `format_citation` | Literature synthesis with citations |
| 9 | `response-to-author` | — | Tone and structure for author rebuttal letters |
| 10 | `response-to-editor` | — | Tone and structure for editor response letters |

### 5.2 Skill API (`backend/app/api/routes/skills.py`, 167 lines)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/builtin-tools` | List of 7 tools with descriptions (for the skill editor UI) |
| `POST` | `/` | Create a skill (owned by current user) |
| `GET` | `/` | List user's own skills + public skills, deduped by name (user's own wins) |
| `GET` | `/{id}` | Get one skill |
| `PATCH` | `/{id}` | Partial update (name, description, system_prompt, tools) |
| `DELETE` | `/{id}` | Delete (only if owner) |
| `POST` | `/assign/{config_id}` | Replace the M2M skill set for a config (idempotent set) |

### 5.3 How skills are merged into an agent

When `/agents/run` or `workflows._run_stage()` prepares a run, it:

1. Loads the `AgentConfig` by id.
2. Eager-loads the M2M skills and concatenates their `system_prompt` fields (in M2M order) to the config's own `system_prompt`.
3. Resolves the union of all bound skill tool names via `get_tools_by_names(...)`.
4. Passes the merged prompt and resolved tools to `create_agent(...)`.

This means a user can re-bind skills on any config (including the seed configs) without code changes.

---

## 6. Strategies — execution patterns

Defined in `backend/app/agents/strategies/__init__.py` (401 lines). A strategy wraps an LLM call into a loop and emits typed events.

### 6.1 `AgentStrategy` ABC

```python
class AgentStrategy(ABC):
    async def execute(
        self,
        llm: BaseChatModel,
        messages: list[BaseMessage],
        system_prompt: str,
        tools: list,
    ) -> AsyncIterator[StrategyEvent]: ...
```

Each strategy is an async generator that yields `StrategyEvent` objects until the loop terminates.

### 6.2 `StrategyEvent` (Pydantic)

| Field | Type | Notes |
|------|------|-------|
| `type` | `STRATEGY_ITERATION \| STRATEGY_COMPLETE` | Event kind |
| `phase` | `str` | e.g. `"generate"`, `"critique"`, `"refine"`, `"reflect"`, `"evaluate"`, `"optimize"` |
| `iteration` | `int` | 1-indexed |
| `max_iterations` | `int` | Loop bound |
| `score` | `float \| None` | Only set by `EvaluatorOptimizerStrategy` |
| `result` | `str \| None` | The produced text, set on `STRATEGY_COMPLETE` |

### 6.3 The four strategies

| Strategy | Iterations | Per-iteration events | Description |
|----------|-----------|---------------------|-------------|
| `DirectStrategy` | 1 | 1 × `STRATEGY_ITERATION` (phase=`"generate"`) | Single LLM call, no loop |
| `CritiqueStrategy` | configurable, default 2 | 3 × `STRATEGY_ITERATION` (generate → critique → refine) | Generates, critiques its own output, refines |
| `ReflectionStrategy` | configurable, default 2 | 2 × `STRATEGY_ITERATION` (generate → reflect) | Generates, then reflects and rewrites |
| `EvaluatorOptimizerStrategy` | configurable, default 3 | 3 × `STRATEGY_ITERATION` (generate → evaluate → optimize), score attached | Generates, scores, optimizes until score threshold or iteration cap |

### 6.4 Event types

`EventType` enum in `backend/app/services/progress.py`:
- `strategy.iteration` — emitted on every `STRATEGY_ITERATION` event
- `strategy.complete` — emitted on `STRATEGY_COMPLETE`

### 6.5 Strategy vs graph output

If the agent's `StateGraph` already writes `state["output"]` (most agents do — they have a finalization node), the `BaseAgent.run` **skips the strategy** entirely. The strategy loop is only used as a fallback / outer wrapper when the graph itself doesn't produce a terminal output. This avoids double-running LLMs.

---

## 7. Runtime agents — the 10 LangGraph graphs

All agents inherit from `BaseAgent` (`backend/app/agents/base.py`, 353 lines) and implement `build_graph() -> StateGraph`. The runtime `run()` method:

1. Calls `astream_events(version="v2")` on the compiled graph.
2. On every `on_chain_start` with a node name, publishes `NODE_STARTED`.
3. On `on_chain_end` for a node, publishes `NODE_COMPLETED`.
4. On `on_tool_start` and `on_tool_end`, publishes `TOOL_CALL` and `TOOL_COMPLETE` (with the tool name and a redacted args/result).
5. Polls `_cancel_flags[execution_id]` between events and aborts cleanly.
6. After the graph terminates, if `state["output"]` is missing, invokes the configured strategy and streams its `STRATEGY_ITERATION` / `STRATEGY_COMPLETE` events through the same `ProgressManager`.
7. Returns the final state dict: `{messages, context, output, metadata}` where `metadata["usage"]` carries aggregated token counts.

Below, each agent is documented with its graph topology, tool usage, and integration notes.

### 7.1 `SearchAgent` (`backend/app/agents/search_agent.py`, 1308 lines)

| Property | Value |
|----------|-------|
| `name` | `search` |
| `role` | `researcher` |
| Graph | 4-node state graph |
| Strategy fallback | Yes (when graph doesn't emit `output`) |
| Default tools | `search_papers`, `search_web`, `read_document`, `format_citation`, `find_citation`, `extract_pdf_text`, `extract_citations` |

**Graph topology:**

```
[pre_query_strategies] ──► [run_source_queries] ──► [deduplicate] ──► [build_dossier] ──► END
```

- **`pre_query_strategies`** — picks one of three pre-query strategies based on the request:
  - `build_related_work` — uses a citation graph to seed paper ids
  - `_expand_queries_with_llm` — generates 3–5 reformulations of the original query
  - `_resolve_to_recommendations` — switches mode to a recommendation-style expansion
- **`run_source_queries`** — fans out to four sources (Semantic Scholar, arXiv, CrossRef, OpenAlex) **with per-source try/except**. Any source that throws is recorded in `context["search_metadata"]["sources_failed"]`; the others continue.
- **`deduplicate`** — calls `app.agents.dedup` (193 lines) to merge near-duplicates by title, DOI, and author overlap.
- **`build_dossier`** — produces a `ResearchDossier` Pydantic model (`backend/app/agents/dossier.py`, 429 lines) containing `PaperSource`, `PaperRecord`, `ResearchGap`, `MethodologyEntry`, and `SearchMetadata`. This dossier is what the `ReviewAgent` consumes downstream.

The `ResearchDossier` schema is the contract between search and review — see `dossier.py` for the full field reference.

### 7.2 `WritingAgent` (`backend/app/agents/writing_agent.py`, 83 lines)

| Property | Value |
|----------|-------|
| `name` | `writing` |
| `role` | `writer` (also reused for `manager`) |
| Graph | 2-node |
| Default tools | none |

```
[understand_task] ──► [generate_content] ──► END
```

Used by the `writer` and `manager` roles. Tracks `accumulate_usage` to aggregate token counts across multiple LLM calls inside the graph.

### 7.3 `ReviewAgent` (`backend/app/agents/review_agent.py`, 162 lines)

| Property | Value |
|----------|-------|
| `name` | `review` |
| `role` | `reviewer` |
| Graph | 2-node |
| Default tools | inherited from skills (no defaults at agent level) |

```
[analyze] ──► [respond] ──► END
```

**Critical contract:** reads `state.context["research_dossier"]` as the evidence corpus. This means a `ReviewAgent` is only useful when invoked by a workflow that first ran a `SearchAgent` (e.g. `review-paper`). The dossier is injected by the workflow's `_run_stage` between stages.

The description string is literally: *"Workflow-integrated paper review. Consumes Search Agent's research_dossier as evidence corpus."*

### 7.4 `ReviewWriterAgent` (`backend/app/agents/review_writer_agent.py`, 171 lines)

| Property | Value |
|----------|-------|
| `name` | `review-writer` |
| `role` | `review_writer` |
| Graph | 3-node self-critique |
| Default tools | none |

```
[draft] ──► [self_review] ──► [finalize] ──► END
```

Produces a structured review with two top-level headings:

- `## Response to Authors`
- `## Response to Editor`

The final output is validated by `_validate_paper_review_writer_output` in `workflows.py`; both headings must be present in the produced text or the run is marked failed.

### 7.5 `RecommendationAgent` (`backend/app/agents/recommendation_agent.py`, 134 lines)

| Property | Value |
|----------|-------|
| `name` | `recommendation` |
| `role` | `recommender` |
| Sources | Semantic Scholar, OpenAlex, in-house vector search |

Produces a ranked list of recommended papers based on the user's academic profile and seed papers.

### 7.6 `RevisionAgent` (`backend/app/agents/revision_agent.py`, 136 lines)

| Property | Value |
|----------|-------|
| `name` | `revision` |
| `role` | `revision` |
| Graph | 2-node |
| Default tools | `[read_document]` |

```
[understand_revision] ──► [apply_revision] ──► END
```

Used for revising **review documents**, not the papers themselves. Note: when bound to a streaming chat, tool calls may not execute end-to-end — the runtime prefers to surface the revision as a chat-style delta rather than re-invoking document reading.

### 7.7 `DebateAgent` (`backend/app/agents/debate_agent.py`, 131 lines) — `standard` variant

| Property | Value |
|----------|-------|
| `name` | `debate` |
| `role` | `debater` |
| `variant` | `STANDARD` |
| Graph | 3-node |
| LLM calls | 3, ~30K tokens total |

```
[intake] ──► [debate] ──► [synthesize] ──► END
```

Adversarial debate between a paper-defender and a review-defender. The final synthesize step reconciles their positions.

### 7.8 `DeepDebateAgent` (`backend/app/agents/deep_debate_agent.py`, 158 lines) — `deep` variant

| Property | Value |
|----------|-------|
| `name` | `deep-debate` |
| `role` | `debater` |
| `variant` | `DEEP` |
| Graph | 4-node |
| LLM calls | 3, ~40K tokens total |

```
[intake] ──► [defend_paper] ──► [evaluate_defense] ──► [synthesize] ──► END
```

Adds an explicit "evaluate the paper's defense" step before synthesis — produces a more balanced adjudication.

### 7.9 `SimpleDebateAgent` (`backend/app/agents/simple_debate_agent.py`, 108 lines) — `simple` variant

| Property | Value |
|----------|-------|
| `name` | `simple-debate` |
| `role` | `debater` |
| `variant` | `SIMPLE` |
| Graph | 2-node |
| LLM calls | 2, ~20K tokens total |

```
[intake] ──► [respond] ──► END
```

The default debater. Used unless the user picks `standard` or `deep`.

### 7.10 `DeepReviewAgent` (`backend/app/agents/review_pipeline.py`, 546 lines)

| Property | Value |
|----------|-------|
| `name` | `deep-reviewer` |
| `role` | `deep_reviewer` |
| Graph | 7-stage pipeline |
| Scoring | `RubricCriterionScore` Pydantic model |

**Pipeline stages (in order):**

1. `intake` — read and parse the paper
2. `structural` — assess structure, sections, presentation
3. `claims` — extract and verify the central claims
4. `literature` — review the literature positioning
5. `methodology` — assess the experimental design
6. `adversarial` — run a red-team pass
7. `synthesis` — produce a final rubric-scored review

Each stage produces a `RubricCriterionScore`; the synthesis merges them into a final review. The rubric criteria are configurable through `list_rubric_standards` and `detect_rubric` API endpoints.

---

## 8. Agent registry and factory

`backend/app/agents/factory.py` (107 lines) is the only place that maps roles to classes. It is two-level:

```python
AGENT_REGISTRY: dict[str, type[BaseAgent] | dict[str, type[BaseAgent]]] = {
    "researcher":    SearchAgent,
    "writer":        WritingAgent,
    "reviewer":      ReviewAgent,
    "review_writer": ReviewWriterAgent,
    "recommender":   RecommendationAgent,
    "revision":      RevisionAgent,
    "manager":       WritingAgent,           # alias
    "debater": {
        "simple":   SimpleDebateAgent,
        "standard": DebateAgent,
        "deep":    DeepDebateAgent,
    },
    "deep_reviewer": DeepReviewAgent,
}
```

The default `provider` for any agent is `opencode` (the local-first provider). Models and providers can be overridden per-`AgentConfig`.

### 8.1 `create_agent(...)` signature

```python
async def create_agent(
    agent_type: str,         # role name
    model: str | None = None,
    provider: str | None = None,
    strategy: str | None = None,
    system_prompt: str | None = None,
    tools: list | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    variant: str | None = None,
    **kwargs,
) -> BaseAgent: ...
```

Flow:

1. Look up the class in `AGENT_REGISTRY`, descending into the variant dict for `debater`.
2. Call `llm_service.get_llm(model=model, provider=provider, temperature=temperature, max_tokens=max_tokens)` to materialize a `BaseChatModel`.
3. Instantiate `agent_cls(llm, strategy_name, system_prompt, tools, **kwargs)`.

### 8.2 `list_agents()`

Returns a flat list of agent descriptors for the UI:

```python
[
    {"name": "search",         "description": "…", "role": "researcher",   "variant": None},
    {"name": "writing",        "description": "…", "role": "writer",       "variant": None},
    {"name": "review",         "description": "…", "role": "reviewer",     "variant": None},
    {"name": "review-writer",  "description": "…", "role": "review_writer","variant": None},
    {"name": "recommendation", "description": "…", "role": "recommender",  "variant": None},
    {"name": "revision",       "description": "…", "role": "revision",     "variant": None},
    {"name": "manager",        "description": "…", "role": "manager",      "variant": None},
    {"name": "simple-debate",  "description": "…", "role": "debater",      "variant": "simple"},
    {"name": "debate",         "description": "…", "role": "debater",      "variant": "standard"},
    {"name": "deep-debate",    "description": "…", "role": "debater",      "variant": "deep"},
    {"name": "deep-reviewer",  "description": "…", "role": "deep_reviewer","variant": None},
]
```

The three debater variants are **flattened** — each becomes its own entry — so the AgentsPage can render them as separate selectable agents.

---

## 9. Agent configurations — seed + defaults

There are two distinct sources of agent configs:

1. **ScholarFlow seeds** — high-quality presets bound to specific models (`openrouter` / `deepseek/deepseek-chat-v3-0324:free`) and curated skill bundles. Created on first login. `is_default=False`.
2. **Bare defaults** — minimal configs using `openrouter` / `google/gemma-4-31b-it:free` for every role not covered by seeds. Created on first login and again whenever a user adds a new role coverage. `is_default=True`.

### 9.1 Seed configs (`_AGENT_SEEDS` in `scholarflow_skills.py`)

| # | Name | Role | Strategy | Variant | Skills |
|---|------|------|----------|---------|--------|
| 1 | **Proposal Writer** | `writer` | `direct` | — | `eu-horizon`, `academic-writing` |
| 2 | **Proposal Reviewer** | `reviewer` | `critique` | — | `eu-horizon`, `solo-paper-review` |
| 3 | **Project Manager** | `manager` | `direct` | — | `eu-horizon`, `project-management` |
| 4 | **Review Writer** | `review_writer` | `direct` | — | `response-to-author`, `response-to-editor` |
| 5 | **Simple Debater** | `debater` | `critique` | `SIMPLE` | — |
| 6 | **Standard Debater** | `debater` | `critique` | `STANDARD` | — |
| 7 | **Deep Debater** | `debater` | `critique` | `DEEP` | — |

### 9.2 Bare defaults (`_DEFAULT_AGENT_CONFIGS` in `agents.py`)

| # | Name | Role | Strategy |
|---|------|------|----------|
| 1 | Default Researcher | `researcher` | `direct` |
| 2 | Default Writer | `writer` | `direct` |
| 3 | Default Reviewer | `reviewer` | `critique` |
| 4 | Default Recommender | `recommender` | `direct` |
| 5 | Default Review Writer | `review_writer` | `direct` |
| 6 | Default Debater | `debater` | `critique` |
| 7 | Default Deep Reviewer | `deep_reviewer` | `critique` |

All bare defaults use the same model (`openrouter` / `google/gemma-4-31b-it:free`) and carry no skills, so they're a safe fallback if the user has no API credits or the model is rate-limited.

### 9.3 Bootstrap flow on `/agents/configs` first call

```
user hits /agents/configs
        │
        ▼
user has 0 configs? ──► seed_scholarflow(db, user_id)
        │                  │
        │                  ├─► create 10 skills (skip if name exists)
        │                  └─► create 7 seed configs (M2M via raw SQL insert)
        │
        ▼
diff against required role coverage
        │
        ▼
for any missing role, create bare default config
        │
        ▼
return full list (seed + defaults, sorted by role)
```

Subsequent visits skip `seed_scholarflow` (skills and seed configs already exist) and only create bare defaults for any role that has no config at all (e.g. a user who deleted a default).

### 9.4 AgentConfig fields

| Field | Type | Notes |
|------|------|-------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Owner |
| `name` | str | Display name |
| `description` | str \| None | Optional |
| `role` | `AgentRole` | Drives agent class lookup |
| `variant` | `AgentVariant \| None` | Only used for `debater` |
| `provider` | str | `openrouter` (default) / `openai` / `anthropic` / `opencode` |
| `model` | str | Provider-specific model id |
| `strategy` | `Strategy` | Loop behavior |
| `system_prompt` | str \| None | Base prompt; **merged with** bound skill prompts at runtime |
| `temperature` | float \| None | Pass-through to LLM |
| `max_tokens` | int \| None | Pass-through to LLM |
| `is_default` | bool | Distinguishes bare defaults from seeds/user configs |
| `created_at` / `updated_at` | datetime | |

---

## 10. Workflows — multi-stage orchestrations

`backend/app/api/routes/workflows.py` (2006 lines) defines **16** workflows in a `WORKFLOW_DEFINITIONS` dict. Each workflow has a unique `id`, a `name`, and an ordered list of `stages`. Each stage has:

```python
{
    "id": str,           # unique within the workflow
    "role": AgentRole,   # selects the agent class
    "task_template": str # human-readable description used in the UI
}
```

### 10.1 Workflow inventory

The 16 workflows fall into the following functional groups:

**Literature discovery**
- `search-related-work` — search → synthesize related work section
- `research-landscape` — broad survey of a research area

**Paper review (full pipelines)**
- `review-paper` — search (dossier) → review → review-writer (validated)
- `paper-review-writer` — review-writer only, with both editor + author sections
- `review-draft` — review on an in-progress draft
- `debate-review` — search → review → debate (variant selectable)

**Methodology and structure**
- `design-methodology` — recommend a methodology for a given research question
- `create-framework` — build a conceptual framework
- `create-materials` — produce supporting materials (figures, tables, code stubs)

**Writing and proposals**
- `write-proposal` (×2 variants for different funding contexts)
- `write-paper` — full paper draft pipeline
- `create-artifacts` — generate supplementary artifacts (LaTeX, code, datasets)
- `review-deliverables` — review the outputs of a writing workflow

(The exact stage list for each workflow is best inspected in the `WORKFLOW_DEFINITIONS` dict; the count of 16 is verified by grep against the source file.)

### 10.2 `_run_stage(stage, context, execution_id, user_id, db)`

The per-stage driver. Mirrors the body of `POST /agents/run`:

1. Load the user's `AgentConfig` for the stage's role (preferring seed → default → first match).
2. Eager-load M2M skills and concatenate their `system_prompt` with the config's.
3. Resolve the union of bound-skill tool names via `get_tools_by_names`.
4. Call `create_agent(agent_type=role, model=…, provider=…, strategy=…, system_prompt=merged, tools=resolved, variant=…)`.
5. Call `agent.run(messages, context, thread_id, progress_manager, execution_id)`.
6. Append the stage output to the running context and yield progress events.

### 10.3 Validation hooks

- `_validate_paper_review_writer_output(output)` — checks that both `## Response to Authors` and `## Response to Editor` headings are present in `paper-review-writer` outputs.
- Other workflows have lightweight length and heading checks; see `workflows.py` for the per-workflow predicates.

### 10.4 Workflow endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/workflows/execute` | Start a workflow run |
| `GET` | `/workflows` | List all 16 workflow definitions |
| `GET` | `/workflows/results` | List past workflow executions for the user |
| `GET` | `/workflows/results/{id}` | Get one execution (with stages and final state) |
| `DELETE` | `/workflows/results/{id}` | Delete one execution |
| `POST` | `/workflows/results/{id}/cancel` | Cancel a running execution |
| `GET` | `/workflows/results/{id}/stream` | **SSE** stream of progress events |
| `POST` | `/workflows/results/{id}/snapshot` | Save a snapshot of the current state |
| `DELETE` | `/workflows/results` | Delete all executions (with confirmation) |
| `GET` | `/workflows/results/{id}/export/markdown` | Export execution as Markdown |
| `GET` | `/workflows/results/{id}/export/pdf` | Export execution as PDF |
| `GET` | `/workflows/model-pricing` | Get pricing for the model catalog (per-token, per-provider) |
| `GET` | `/workflows/rubric-standards` | List available rubric standards for `DeepReviewAgent` |
| `POST` | `/workflows/detect-rubric` | Detect rubric from a paper's text |

---

## 11. Progress and streaming

`backend/app/services/progress.py` defines the `ProgressManager`, `EventType`, and `ExecutionEvent` primitives. Every agent run and every workflow stage uses a single `ProgressManager` instance, identified by `execution_id`, to publish typed events to subscribed listeners (typically an SSE generator in `workflows.stream_progress` or a direct WebSocket channel).

### 11.1 Event types

| `EventType` | Source | Payload |
|-------------|--------|---------|
| `node.started` | LangGraph `on_chain_start` for a node | `{node: str, run_id: str}` |
| `node.completed` | LangGraph `on_chain_end` for a node | `{node: str, run_id: str, output_preview: str}` |
| `tool.call` | LangGraph `on_tool_start` | `{tool: str, args: Any, run_id: str}` |
| `tool.complete` | LangGraph `on_tool_end` | `{tool: str, result_preview: str, run_id: str}` |
| `strategy.iteration` | `StrategyEvent` (`STRATEGY_ITERATION`) | `{phase, iteration, max_iterations, score?}` |
| `strategy.complete` | `StrategyEvent` (`STRATEGY_COMPLETE`) | `{phase, result_preview}` |
| `stage.started` | Workflow driver | `{stage_id, role}` |
| `stage.completed` | Workflow driver | `{stage_id, role, output_preview}` |
| `run.completed` | Workflow driver | `{output, usage, metadata}` |
| `run.failed` | Workflow driver | `{error, stage_id?}` |
| `run.cancelled` | Workflow driver | `{reason}` |

### 11.2 How events are correlated

Each event carries an `event_id` (monotonic per execution) generated by `_next_progress_event_id()`. Consumers can use this to dedupe re-deliveries, or to resume from a specific point.

### 11.3 Frontend consumption

The frontend opens an `EventSource` against `/workflows/results/{id}/stream` and updates the UI in real time:

- A new `node.started` activates the matching card and shows a spinner.
- `tool.call` / `tool.complete` show a tool sub-line under the active card.
- `strategy.iteration` shows the iteration number and phase.
- `run.completed` finalizes the card and reveals the export buttons.

---

## 12. HTTP API surface

All routes live under `/api/v1` (the FastAPI prefix in `app/main.py`). Below is a summary; per-route details are documented in the route files.

| Router | File | Key endpoints |
|--------|------|--------------|
| `auth` | `api/routes/auth.py` | `/auth/register`, `/auth/login`, `/auth/me` |
| `agents` | `api/routes/agents.py` | `GET/POST /agents/configs`, `POST /agents/run`, `GET /agents/registry` (the flattened agent list) |
| `skills` | `api/routes/skills.py` | CRUD + `/assign/{config_id}` + `/builtin-tools` (see §5.2) |
| `workflows` | `api/routes/workflows.py` | see §10.4 |
| `chat` | `api/routes/chat.py` | `/chat/sessions`, `/chat/sessions/{id}/messages` |
| `revisions` | `api/routes/revisions.py` | `/revisions/sessions`, `/revisions/sessions/{id}/messages` |
| `assets` | `api/routes/assets.py` | `/assets` upload, `/assets/{id}/chunks` |
| `workspaces` | `api/routes/workspaces.py` | `/workspaces`, `/workspaces/{id}` |
| `settings` | `api/routes/settings.py` | `/settings/api-keys` (CRUD, Fernet-encrypted) |
| `dashboard` | `api/routes/dashboard.py` | `/dashboard/summary` |

### 12.1 `POST /agents/run` request shape

```json
{
  "config_id": "uuid",
  "messages": [
    {"role": "user", "content": "…"}
  ],
  "context": { },
  "thread_id": "optional-thread-uuid"
}
```

The response is the final state dict plus a stream of progress events. The synchronous response (when the caller is not using SSE) returns the final `output` and `metadata.usage`.

---

## 13. Frontend — `/cult/*` routes

The CULT surface is three top-level routes, registered directly in `App.tsx` (the old `CultPage` wrapper is gone):

| Path | Page file | Purpose |
|------|-----------|---------|
| `/cult/agents` | `frontend/src/pages/AgentsPage.tsx` (37KB) | Browse, create, edit, run agent configs |
| `/cult/skills` | `frontend/src/pages/SkillsPage.tsx` (36KB) | Browse, create, edit skills (tool picker) |
| `/cult/chat` | `frontend/src/pages/ChatPage.tsx` (28KB) | Free-form chat with a selected config + streaming progress |

### 13.1 Sidebar

Three icons, in order: **Bot** (agents), **ScrollText** (skills), **MessageSquare** (chat).

### 13.2 Topbar

The top bar label is **"Intelligence"** (not "CULT" — CULT is the internal codename).

### 13.3 AgentsPage responsibilities

- List all configs (seeds + defaults + user-created), filterable by role.
- Create / edit / delete user configs.
- Pick a model from the provider catalog and set temperature / max_tokens.
- Bind skills via a multi-select that calls `POST /skills/assign/{config_id}`.
- "Run" button opens a chat-like drawer that streams the response with live progress events.

### 13.4 SkillsPage responsibilities

- List user skills + public skills (dedup by name).
- Editor: name, description, system_prompt, and a tool multi-select populated from `/builtin-tools`.
- Per-skill preview of resolved system prompt + tools.

### 13.5 ChatPage responsibilities

- Pick a config (or none, for a vanilla chat).
- Free-form message input.
- Subscribe to `/agents/run` SSE stream and render the progress events inline.
- Save the session to `chat_sessions` / `chat_messages` automatically.

---

## 14. Cancellation, persistence, observability

### 14.1 Cancellation

`_cancel_flags` is a module-level dict in `workflows.py` (and a parallel one in `base.py`) keyed by `execution_id`. The run loop checks the flag between events and aborts cleanly with a `run.cancelled` event. The cancel endpoint `POST /workflows/results/{id}/cancel` sets the flag and the run terminates within one event cycle.

### 14.2 Persistence

- `workflow_executions` stores the final state and per-stage outputs.
- `workflow_events` is append-only; the full event stream is replayable.
- `chat_sessions` / `chat_messages` persist the chat surface.
- `revision_sessions` / `revision_messages` persist revision chats separately.
- `user_api_keys` stores per-provider API keys Fernet-encrypted; only the LLM service decrypts on use.

### 14.3 Observability

- `metadata.usage` on every run carries aggregated token counts (prompt, completion, total).
- `GET /workflows/model-pricing` returns per-token pricing for cost attribution.
- `context["search_metadata"]["sources_failed"]` records any search source that failed during a `SearchAgent` run.
- The SSE stream is the canonical realtime view; `workflow_events` is the canonical replay view.

---

## 15. File index

### Backend — domain & orchestration

| File | Purpose |
|------|---------|
| `backend/app/models/__init__.py` | Enums (`AgentRole`, `Strategy`, `AgentVariant`) + re-exports |
| `backend/app/models/agent_config.py` | `AgentConfig` model with `variant` field |
| `backend/app/models/skill.py` | `Skill` model |
| `backend/app/models/workflow_event.py` | `WorkflowEvent` model |
| `backend/app/agents/base.py` | `BaseAgent` ABC + cancel flags + progress hookup (353 lines) |
| `backend/app/agents/factory.py` | `AGENT_REGISTRY` + `create_agent` + `list_agents` (107 lines) |
| `backend/app/agents/search_agent.py` | `SearchAgent` (1308 lines) |
| `backend/app/agents/writing_agent.py` | `WritingAgent` (83 lines) |
| `backend/app/agents/review_agent.py` | `ReviewAgent` (162 lines) |
| `backend/app/agents/review_writer_agent.py` | `ReviewWriterAgent` (171 lines) |
| `backend/app/agents/recommendation_agent.py` | `RecommendationAgent` (134 lines) |
| `backend/app/agents/revision_agent.py` | `RevisionAgent` (136 lines) |
| `backend/app/agents/debate_agent.py` | `DebateAgent` (131 lines) |
| `backend/app/agents/deep_debate_agent.py` | `DeepDebateAgent` (158 lines) |
| `backend/app/agents/simple_debate_agent.py` | `SimpleDebateAgent` (108 lines) |
| `backend/app/agents/review_pipeline.py` | `DeepReviewAgent` 7-stage pipeline (546 lines) |
| `backend/app/agents/dossier.py` | `ResearchDossier` Pydantic models (429 lines) |
| `backend/app/agents/dedup.py` | Manual dedup for search results (193 lines) |
| `backend/app/agents/strategies/__init__.py` | 4 strategies + `STRATEGIES` + `get_strategy` (401 lines) |
| `backend/app/services/progress.py` | `ProgressManager`, `EventType`, `ExecutionEvent` |
| `backend/app/services/llm_service.py` | `get_llm(model, provider, …)` factory |
| `backend/app/seeds/scholarflow_skills.py` | 10 skills + 7 seed configs (954 lines) |

### Backend — HTTP routes

| File | Purpose |
|------|---------|
| `backend/app/api/routes/agents.py` | `/agents/*` + `_DEFAULT_AGENT_CONFIGS` |
| `backend/app/api/routes/skills.py` | `/skills/*` + `/builtin-tools` (167 lines) |
| `backend/app/api/routes/workflows.py` | `/workflows/*` + 16 workflow definitions (2006 lines) |
| `backend/app/api/routes/chat.py` | `/chat/*` (20KB) |
| `backend/app/api/routes/revisions.py` | `/revisions/*` (14KB) |
| `backend/app/api/routes/assets.py` | `/assets/*` (12KB) |
| `backend/app/api/routes/dashboard.py` | `/dashboard/*` (7KB) |
| `backend/app/api/routes/settings.py` | `/settings/*` (6KB) |
| `backend/app/api/routes/workspaces.py` | `/workspaces/*` (4KB) |
| `backend/app/api/routes/auth.py` | `/auth/*` |

### Backend — tools

| File | Purpose |
|------|---------|
| `backend/app/tools/__init__.py` | 7 built-in tools registry (33 lines) |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/App.tsx` | Route table (declares `/cult/agents`, `/cult/skills`, `/cult/chat`) |
| `frontend/src/pages/AgentsPage.tsx` | Agents config UI (37KB) |
| `frontend/src/pages/SkillsPage.tsx` | Skills editor UI (36KB) |
| `frontend/src/pages/ChatPage.tsx` | Chat with progress streaming (28KB) |

---

## Appendix A — What changed since the 2024 analysis

| Aspect | 2024 analysis | Current state |
|--------|---------------|---------------|
| Roles | 4 (researcher, writer, reviewer, recommender) | **9** (+ manager, revision, debater, deep_reviewer, review_writer) |
| Runtime agents | 4 | **10** (debater split into 3 variants) |
| Variants | — | **3** (simple / standard / deep) — debater only |
| Strategies | 4 (direct, critique, reflection, evaluator_optimizer) | 4 (unchanged) |
| Skills | 15 | **10** (curated set, not 15 user-created) |
| Agent configs | 1 default per user | **14** typical per user (7 seed + 7 defaults) |
| Workflows | 4 hardcoded | **16** declared, with per-stage role bindings |
| Progress streaming | none | full SSE pipeline via `ProgressManager` |
| Cancellation | none | `_cancel_flags` + cancel endpoint |
| Frontend | single `CultPage` wrapper | three direct routes (`/cult/agents`, `/cult/skills`, `/cult/chat`) |
| Dossier contract | — | `ResearchDossier` Pydantic schema between SearchAgent and ReviewAgent |

## Appendix B — Replaces

This document **supersedes** `CULT_SYSTEM_ANALYSIS.md` (607 lines, 2024). The old file should be removed; if it is kept for historical reference, it must be marked with a header redirecting to this file.
