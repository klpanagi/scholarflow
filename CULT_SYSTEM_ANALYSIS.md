# ScholarFlow Cult System — Complete Analysis

> Generated: 2026-06-16 | Coverage: Frontend (CultPage, AgentsPage, SkillsPage, ChatPage) + Backend (models, API, agents, skills, tools, seeds, workflow integration)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Frontend Architecture](#2-frontend-architecture)
3. [Backend Models](#3-backend-models)
4. [API Layer](#4-api-layer)
5. [Agent Registry & Implementation](#5-agent-registry--implementation)
6. [Tool Registry](#6-tool-registry)
7. [Skill Inventory](#7-skill-inventory)
8. [Agent Config Inventory](#8-agent-config-inventory)
9. [Workflow Integration](#9-workflow-integration)
10. [Issues & Observations](#10-issues--observations)
11. [Missing Features vs professor-pal](#11-missing-features-vs-professor-pal)
12. [Improvement Roadmap](#12-improvement-roadmap)

---

## 1. System Overview

The **Cult** section is the AI agent configuration hub of ScholarFlow. Users define **Skills** (reusable knowledge+tool bundles), assemble them into **Agent Configs** (role-based agent definitions), and execute them via the chat interface or workflow engine.

**Data flow**: Skill → assigned to AgentConfig → AgentConfig merged + resolved via AgentRegistry → agent executed with tools → structured output.

**Seed system**: `POST /seeds/niobe` creates 15 ready-made skills and 6 specialized agent configs.

---

## 2. Frontend Architecture

### 2.1 Route & Navigation

| Aspect | Detail |
|--------|--------|
| Route | `/cult` (declared in `App.tsx`, `ProtectedRoute` wrapper) |
| Navbar | `Layout.tsx`: `<Link to="/cult"><Bot /> Cult</Link>` |
| Dashboard | `DashboardPage.tsx`: "AI Agents" quick-action card → `/cult` |
| Tab container | `CultPage.tsx` (59 lines, 3 tabs) |

### 2.2 CultPage (`frontend/src/pages/CultPage.tsx`)

Simple tab container with 3 tabs:

```tsx
const TABS = [
  { id: "agents", label: "Agents", icon: Bot },
  { id: "skills", label: "Skills", icon: Puzzle },
  { id: "chat", label: "Chat", icon: MessageSquare },
]
```

Renders `AgentsPage`, `SkillsPage`, or `ChatPage` based on active tab.

### 2.3 AgentsPage (`frontend/src/pages/AgentsPage.tsx` — 628 lines)

**Layout**: Two-column split with agent list (left) and config editor (right).

**Left panel**:
- List of `AgentConfigResponse` objects
- Each row shows: name, role badge (`researcher`/`writer`/`reviewer`/`recommender`), provider, skill count
- Click to select → loads into right panel

**Right panel — Config Editor**:
| Field | Type | Notes |
|-------|------|-------|
| Name | text | |
| Role | enum select | researcher/writer/reviewer/recommender |
| Provider | text | `openrouter` or `opencode` |
| Model | text | e.g. `deepseek-v4-flash`, `google/gemma-4-31b-it:free` |
| Temperature | number (0-2) | |
| Max Tokens | number | |
| Strategy | enum select | `direct`, `critique`, `reflection`, `evaluator_optimizer` |
| System Prompt | textarea | |
| Is Default | checkbox | |

**Right panel — Skill Assignment**:
- Checkbox list of all available skills
- Selected skills are saved via `POST /skills/assign/{config_id}`

**Right panel — Test Agent Runner**:
- Text input + "Run" button
- Maps role to agent type via hardcoded map:

```typescript
const roleToType = {
  researcher: "scholar",
  writer: "writing",
  reviewer: "review",
  recommender: "recommendation",
}
```

- Calls `POST /agents/run` with `{ agentType, message, configId }`

### 2.4 SkillsPage (`frontend/src/pages/SkillsPage.tsx` — 570 lines)

**Layout**: Two-column split with skill list (left) and skill editor (right).

**Left panel**:
- List of `SkillResponse` objects
- Each row shows: name, tool badges, public/private indicator
- Click to select → loads into right panel

**Right panel — Skill Editor**:
| Field | Type | Notes |
|-------|------|-------|
| Name | text | |
| Description | textarea | |
| Prompt Template | textarea (large) | The core knowledge content |
| Builtin Tools | checkbox group | 7 tools from registry |
| Custom Tools | JSON editor | Array of `CustomToolDefinition` |
| Input Schema | JSON editor | Currently `null` for all seeded skills |
| Output Schema | JSON editor | Currently `null` for all seeded skills |
| Tags | tag input | |
| Is Public | checkbox | |

### 2.5 Builtin Tools List (from backend `GET /skills/builtin-tools`)

Rendered in `SkillsPage` as checkboxes under "Builtin Tools":

1. `search_papers`
2. `search_web`
3. `extract_pdf_text`
4. `extract_citations`
5. `format_citation`
6. `find_citation`
7. `read_document`

### 2.6 ChatPage (`frontend/src/pages/ChatPage.tsx` — 420 lines)

Standalone chat interface with:
- Session management (create/switch/delete conversations)
- Model picker (dropdown)
- Streaming response display
- File upload support
- Markdown rendering (via `react-markdown`)
- Fork session capability

**Not directly integrated with agent configs or skills** — it's a freeform chat. Agent configs/skills are used via the AgentsPage "Run" button or the workflow system.

---

## 3. Backend Models

All in `backend/app/models/__init__.py`.

### 3.1 AgentRole (enum)

```python
class AgentRole(str, enum.Enum):
    RESEARCHER = "researcher"
    WRITER = "writer"
    REVIEWER = "reviewer"
    RECOMMENDER = "recommender"
```

### 3.2 Strategy (enum)

```python
class Strategy(str, enum.Enum):
    DIRECT = "direct"
    CRITIQUE = "critique"
    REFLECTION = "reflection"
    EVALUATOR_OPTIMIZER = "evaluator_optimizer"
```

### 3.3 AgentConfig (SQLAlchemy model — table `agent_configs`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `user_id` | FK → `users.id` | |
| `name` | String | |
| `role` | Enum(AgentRole) | |
| `provider` | String | `openrouter` or `opencode` |
| `model` | String | |
| `temperature` | Float | |
| `max_tokens` | Integer | |
| `strategy` | Enum(Strategy) | |
| `tools` | ARRAY(String) | Legacy field? Not used in seeds (empty array) |
| `system_prompt` | Text | |
| `is_default` | Boolean | |

Relationships:
- `user` → `User` (many-to-one)
- `skills` → `Skill` (many-to-many via `agent_skills` table)

### 3.4 Skill (SQLAlchemy model — table `skills`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `user_id` | FK → `users.id` | |
| `name` | String | |
| `description` | Text | |
| `prompt_template` | Text | Core knowledge content |
| `builtin_tools` | ARRAY(String) | References `TOOL_REGISTRY` keys |
| `custom_tools` | JSON | Array of `CustomToolDefinition` |
| `input_schema` | JSON | Currently `null` for all seeded skills |
| `output_schema` | JSON | Currently `null` for all seeded skills |
| `tags` | ARRAY(String) | |
| `is_public` | Boolean | |

### 3.5 agent_skills (join table)

| Column | Type |
|--------|------|
| `agent_config_id` | FK → `agent_configs.id` (CASCADE) |
| `skill_id` | FK → `skills.id` (CASCADE) |

### 3.6 Pydantic Schemas (`backend/app/schemas/__init__.py`)

| Schema | Fields |
|--------|--------|
| `AgentConfigBase` | name, role, provider, model, temperature, max_tokens, strategy, tools, system_prompt, is_default |
| `AgentConfigCreate` | extends Base |
| `AgentConfigUpdate` | all optional |
| `AgentConfigResponse` | Base + id, user_id, skills (list of SkillResponse) |
| `SkillBase` | name, description, prompt_template, builtin_tools, custom_tools, input_schema, output_schema, tags, is_public |
| `SkillCreate` | extends Base |
| `SkillUpdate` | all optional |
| `SkillResponse` | Base + id, user_id |
| `AgentRunRequest` | agent_type, agent_config_id, model, strategy, message, context, thread_id |
| `AgentRunResponse` | output, metadata |
| `CustomToolDefinition` | name, description, endpoint, method, headers, params_schema, response_parser |
| `AgentConfigUpdateWithSkills` | skill_ids: list[UUID] |

---

## 4. API Layer

### 4.1 Agents API (`/agents` prefix, `backend/app/api/routes/agents.py` — 306 lines)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| `GET` | `/agents/types` | `get_available_agents()` | Lists agent types from `AGENT_REGISTRY` |
| `POST` | `/agents/run` | `run_agent()` | Execute agent with optional config + skills |
| `POST` | `/agents/configs` | `create_agent_config()` | Create config (validates role + strategy enums) |
| `GET` | `/agents/configs` | `list_agent_configs()` | List user's configs; **auto-creates 4 defaults if none exist** |
| `GET` | `/agents/configs/{config_id}` | `get_agent_config()` | Get single config with skills loaded |
| `PATCH` | `/agents/configs/{config_id}` | `update_agent_config()` | Partial update |
| `DELETE` | `/agents/configs/{config_id}` | `delete_agent_config()` | Delete config (204) |

### 4.2 Skills API (`/skills` prefix, `backend/app/api/routes/skills.py` — 155 lines)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| `GET` | `/skills/builtin-tools` | `list_builtin_tools()` | Lists 7 built-in tool definitions |
| `POST` | `/skills/` | `create_skill()` | Create skill |
| `GET` | `/skills/` | `list_skills()` | List user's own + public skills |
| `GET` | `/skills/{skill_id}` | `get_skill()` | Get single skill |
| `PATCH` | `/skills/{skill_id}` | `update_skill()` | Partial update |
| `DELETE` | `/skills/{skill_id}` | `delete_skill()` | Delete skill |
| `POST` | `/skills/assign/{config_id}` | `assign_skills_to_agent()` | Assign skill IDs to agent config |

### 4.3 Seeds API (`/seeds` prefix, `backend/app/api/routes/seeds.py` — 21 lines)

| Method | Endpoint | Handler | Description |
|--------|----------|---------|-------------|
| `POST` | `/seeds/niobe` | `run_niobe_seed()` | Seeds 15 skills + 6 agent configs |

### 4.4 Agent Execution Flow

When `POST /agents/run` is called with `agent_config_id`:

1. Load `AgentConfig` with `selectinload(AgentConfig.skills)`
2. Collect `prompt_template` from each assigned skill → merge into system prompt
3. Collect `builtin_tools` from each skill → resolve via `get_tools_by_names()`
4. Create agent via factory: `create_agent(agent_type, model, provider, strategy, merged_prompt, resolved_tools, ...)`
5. Run agent and return output + `skills_used` metadata

Same flow used in workflow execution (`workflows.py:_run_stage()`).

---

## 5. Agent Registry & Implementation

### 5.1 Factory (`backend/app/agents/factory.py` — 52 lines)

```python
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "researcher": SearchAgent,
    "writer": WritingAgent,
    "reviewer": ReviewAgent,
    "recommender": RecommendationAgent,
}
```

**`create_agent()`** takes: `agent_type`, `model`, `provider`, `strategy`, `system_prompt`, `tools`, `temperature`, `max_tokens`.

### 5.2 Agent Classes

| Role | Class | File | Description |
|------|-------|------|-------------|
| `researcher` | `SearchAgent` | `search_agent.py` | Academic search across S2, arXiv, CrossRef, OpenAlex |
| `writer` | `WritingAgent` | `writing_agent.py` | 2-stage pipeline (understand_task → generate_content) |
| `reviewer` | `ReviewAgent` | `review_agent.py` | 7-stage LangGraph (intake → structural → claims → literature → methodology → adversarial → synthesis) |
| `recommender` | `RecommendationAgent` | `recommendation_agent.py` | Paper/venue recommendations via S2 + OpenAlex + vector search |



### 5.3 BaseAgent (`backend/app/agents/base.py`)

Abstract class. All agents implement `async run(message: str, context: dict | None = None) -> AgentRunResponse`.

---

## 6. Tool Registry

`backend/app/tools/__init__.py` (33 lines)

```python
TOOL_REGISTRY = {
    "search_papers": search_papers,       # S2, arXiv, CrossRef, OpenAlex
    "search_web": search_web,             # Tavily/web search
    "extract_pdf_text": extract_pdf_text, # PDF text via Tika/Marker
    "extract_citations": extract_citations,
    "format_citation": format_citation,   # APA/MLA/Chicago/IEEE
    "find_citation": find_citation,
    "read_document": read_document,       # PDF/DOCX/XLSX/PPTX/HTML
}

def get_tools_by_names(tool_names: list[str]) -> list[object]
```

Tool implementations:
- `backend/app/tools/search.py` — `search_papers`, `search_web`
- `backend/app/tools/pdf.py` — `extract_pdf_text`, `extract_citations`
- `backend/app/tools/citation.py` — `format_citation`, `find_citation`
- `backend/app/tools/document_reader.py` — `read_document`

---

## 7. Skill Inventory

All 15 skills seeded by `POST /seeds/niobe`. All have `input_schema: null`, `output_schema: null`, `custom_tools: []`.

| # | Skill | Builtin Tools | Tags | Assigned To |
|---|-------|--------------|------|-------------|
| 1 | `academic-writing` | `search_papers`, `format_citation`, `find_citation` | academic, writing, papers, journals, conferences, IMRaD | Academic Writer |
| 2 | `academic-paper-review` | `search_papers`, `extract_pdf_text`, `extract_citations`, `format_citation`, `find_citation` | academic, review, peer-review, evaluation | Paper Reviewer |
| 3 | `eu-horizon` | `search_papers`, `search_web` | eu, horizon-europe, funding, proposals, research | Paper Reviewer, Grant Writer, Project Manager |
| 4 | `grant-writing` | `search_papers`, `search_web` | grants, funding, proposals, nsf, nih, erc | Grant Writer |
| 5 | `deliverable-writing` | `search_papers`, `format_citation` | eu, deliverables, reports, kpi, tracking | Grant Writer |
| 6 | `project-management` | *(none)* | project, management, agile, scrum, wbs | Project Manager |
| 7 | `technical-lead` | *(none)* | technical, leadership, architecture, code-review | Project Manager |
| 8 | `research-methodology` | `search_papers` | research, methodology, statistics, design, experiment | Scholar, Research Methodologist |
| 9 | `literature-review` | `search_papers`, `search_web`, `format_citation` | literature, review, systematic, prisma, bibliometric | Scholar, Research Methodologist |
| 10 | `scientific-presentation` | *(none)* | presentation, conference, talk, poster, pitch | Academic Writer |
| 11 | `data-management-plan` | `search_web` | data, management, fair, dmp, gdpr | Grant Writer, Research Methodologist |
| 12 | `ip-exploitation` | `search_web` | ip, patent, licensing, commercialisation, trl | Project Manager |
| 13 | `research-ideation` | `search_papers`, `search_web` | ideation, research, ideas, novelty, innovation | Scholar, Academic Writer |
| 14 | `citation-verification` | `search_papers`, `read_document` | citation, verification, fact-check, evidence | Scholar |
| 15 | `reproducibility-assessment` | `read_document`, `search_papers` | reproducibility, open-science, verification, methodology | Paper Reviewer |

### Tool Usage Heatmap

| Skill | search_papers | search_web | extract_pdf_text | extract_citations | format_citation | find_citation | read_document |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| academic-writing | ✓ | | | | ✓ | ✓ | |
| academic-paper-review | ✓ | | ✓ | ✓ | ✓ | ✓ | |
| eu-horizon | ✓ | ✓ | | | | | |
| grant-writing | ✓ | ✓ | | | | | |
| deliverable-writing | ✓ | | | | ✓ | | |
| project-management | | | | | | | |
| technical-lead | | | | | | | |
| research-methodology | ✓ | | | | | | |
| literature-review | ✓ | ✓ | | | ✓ | | |
| scientific-presentation | | | | | | | |
| data-management-plan | | ✓ | | | | | |
| ip-exploitation | | ✓ | | | | | |
| research-ideation | ✓ | ✓ | | | | | |
| citation-verification | ✓ | | | | | | ✓ |
| reproducibility-assessment | ✓ | | | | | | ✓ |
| **Total uses** | **10** | **5** | **1** | **1** | **4** | **2** | **2** |

---

## 8. Agent Config Inventory

### 8.1 Auto-Created Defaults

Created by `list_agent_configs()` when user has zero configs. Uses `openrouter` provider, `google/gemma-4-31b-it:free` model. No skills, no tools.

| Config | Role | Strategy | System Prompt |
|--------|------|----------|--------------|
| Default Researcher | `researcher` | direct | "You are an expert academic researcher..." |
| Default Writer | `writer` | direct | "You are an expert academic writer..." |
| Default Reviewer | `reviewer` | critique | "You are a rigorous peer reviewer..." |
| Default Recommender | `recommender` | direct | "You are a personalized academic recommendation engine..." |

**Issue**: These run on a free-tier model (gemma) with no skills, no tools, and a barebones system prompt. They exist solely as placeholders until the user runs seeds.

### 8.2 Niobe Seed Configs

Created by `POST /seeds/niobe`. Uses `opencode` provider, `deepseek-v4-flash` model. Skill-linked, tool-enabled.

| Config | Role | Model | Strategy | Skills | Tools (resolved) |
|--------|------|-------|----------|-------|-----------------|
| **Scholar** | `researcher` | deepseek-v4-flash | direct | literature-review, research-ideation, citation-verification, research-methodology | `search_papers`, `search_web`, `format_citation`, `read_document` |
| **Academic Writer** | `writer` | deepseek-v4-flash | reflection | academic-writing, scientific-presentation, research-ideation | `search_papers`, `search_web`, `format_citation`, `find_citation` |
| **Paper Reviewer** | `reviewer` | deepseek-v4-flash | critique | academic-paper-review, reproducibility-assessment, eu-horizon | `search_papers`, `search_web`, `extract_pdf_text`, `extract_citations`, `format_citation`, `find_citation`, `read_document` |
| **Grant Writer** | `writer` | deepseek-v4-flash | reflection | grant-writing, eu-horizon, deliverable-writing, data-management-plan | `search_papers`, `search_web`, `format_citation` |
| **Research Methodologist** | `researcher` | deepseek-v4-flash | direct | research-methodology, data-management-plan, literature-review | `search_papers`, `search_web`, `format_citation` |
| **Project Manager** | `researcher` | deepseek-v4-flash | direct | project-management, technical-lead, ip-exploitation, eu-horizon | `search_web` |

### 8.3 Config Summary Matrix

| Config | Role Class | Base Prompt | Knowledge (skills) | Tools | Strategy |
|--------|-----------|-------------|-------------------|-------|----------|
| Scholar | `SearchAgent` | Academic discovery | 4 skills | 4 tools | direct |
| Academic Writer | `WritingAgent` | Content creation | 3 skills | 4 tools | reflection |
| Paper Reviewer | `ReviewAgent` | Evaluation | 3 skills | 7 tools (max) | critique |
| Grant Writer | `WritingAgent` | Proposals & reporting | 4 skills | 3 tools | reflection |
| Research Methodologist | `SearchAgent` | Experiment design | 3 skills | 3 tools | direct |
| Project Manager | `SearchAgent` | Research leadership | 4 skills | 1 tool | direct |

---

## 9. Workflow Integration

The agent/skill system feeds into the **Workflows** engine (`backend/app/api/routes/workflows.py`, 1200+ lines).

### 9.1 4 Hardcoded Workflows

| Workflow | Stages | Description |
|----------|--------|-------------|
| `paper-review` | Scholar → Paper Reviewer → Writer | Review a paper end-to-end |
| `proposal-writing` | Scholar → Grant Writer → Research Methodologist → Writer | Write a grant proposal |
| `conference-prep` | Scholar → Academic Writer → Paper Reviewer | Prepare conference submission |
| `eu-project` | Scholar → Grant Writer → Project Manager → Writer | Prepare EU project proposal |

### 9.2 Stage Resolution

Each stage specifies an `agent_role` (e.g., `researcher`, `writer`, `reviewer`). During execution:

1. Load the user's `AgentConfig` matching that role + `is_default=true`
2. Load its assigned skills and tools
3. Create agent via factory with merged configuration
4. Execute with stage-specific task template

### 9.3 Frontend WorkflowsPage

- **Execute tab**: 4 workflow cards with `PipelineDiagram`
- **Results tab**: `ExecutionResultCard` components with `StageTimeline` (vertical timeline with status icons, markdown output, export)

### 9.4 Output & Export

- **Markdown export**: `_build_markdown_from_execution()` — wraps stage outputs in structured markdown with status emojis
- **PDF export**: Uses `markdown` lib → HTML → `pymupdf.Story` pipeline with professional CSS stylesheet
- **Agent templates**: Each workflow stage has a `task_template` that now includes explicit structured output format specs

---

## 10. Issues & Observations

### 10.1 `eu-horizon` on Paper Reviewer

`Paper Reviewer` has `eu-horizon` skill, but paper reviewers don't evaluate EU proposals. The Paper Reviewer config's system prompt says:

> "Check compliance"

This is misplaced. `eu-horizon` belongs on `Grant Writer` (already has it) and a potential "EU Coordinator" role — not a paper reviewer.

**Impact**: When Paper Reviewer runs, its system prompt includes eu-horizon knowledge. This dilutes its focus and may cause confusion in the 7-stage review pipeline.

### 10.2 Auto-defaults vs Seeds: Config Explosion

Sequence: User opens Cult page → `GET /agents/configs` returns empty → auto-creates 4 defaults → user runs `POST /seeds/niobe` → creates 6 more → 10 configs total.

The 4 defaults (gemma, no skills) are never cleaned up. They clutter the UI and create confusion about which config to use.

**Impact**: Users see 10 agent configs, 4 of which are useless (gemma, no skills, no tools).

### 10.3 `recommender` Role is Underdeveloped

Only exists as `Default Recommender` (gemma, no skills, no tools). There is **no seed config** for the recommender role. The `RecommendationAgent` class exists but has no specialized system prompt or skill assignment.

**Impact**: The recommendation feature is effectively non-functional out of the box.

### 10.4 Role-to-Agent Mapping Collision

Three seed configs map to `researcher` role → all resolve to `SearchAgent`:

| Config | Role | Resolves to |
|--------|------|-------------|
| Scholar | `researcher` | `SearchAgent` |
| Research Methodologist | `researcher` | `SearchAgent` |
| Project Manager | `researcher` | `SearchAgent` |

The specialization only affects the **system prompt + skill injection**, not the agent class. These three configs run the same `SearchAgent` class with different prompts.

**Impact**: Methodologist and Project Manager cannot leverage specialized agent behavior — they're just Scholar with different prompts.

### 10.5 `Project Manager` Has Minimal Tool Access

| Skill | Tools |
|-------|-------|
| project-management | *(none)* |
| technical-lead | *(none)* |
| ip-exploitation | `search_web` |
| eu-horizon | `search_papers`, `search_web` |

Resolved: only `search_web`. No `search_papers` despite having `eu-horizon` skill that lists it.

**Impact**: Project Manager is a prompt-only agent with a single tool. It cannot perform meaningful actions beyond text generation.

### 10.7 All input_schema / output_schema Are Null

Every seeded skill has `input_schema: null`, `output_schema: null`. Without schema definitions:
- No structured contracts between skills
- No composability validation
- No type-safe skill chaining
- UI shows empty JSON editors

**Impact**: Skills cannot be reliably composed or validated at the API level.

### 10.8 No Tool Visibility Across the UI

- **SkillsPage** shows builtin_tools as badges but doesn't link to tool definitions or show what each tool does
- **AgentsPage** shows which skills are assigned but not which tools those skills unlock
- User cannot answer "what can this agent actually do?" without cross-referencing manually

**Impact**: Poor UX — users can't understand agent capabilities at a glance.

### 10.9 Frontend Role→Type Mapping Fragility

`AgentsPage.tsx:295` has a hardcoded map:

```typescript
const roleToType = { researcher: "scholar", writer: "writing", reviewer: "review", recommender: "recommendation" }
```

This must stay in sync with `factory.py:AGENT_REGISTRY`. If a new role is added to the backend, the frontend won't know about it.

**Impact**: Brittle coupling between frontend and backend.

### 10.10 No Skill Isolation Testing

Skills cannot be tested independently. The only way to test a skill is:
1. Create/select an agent config
2. Assign the skill to it
3. Run the agent

There is no `POST /skills/run` endpoint.

**Impact**: Debugging a skill requires going through the full agent config pipeline.

---

## 11. Missing Features vs professor-pal

| Feature | professor-pal | academic-pal (this project) |
|---------|---------------|-----------------------------|
| **Task type orchestration** | 20+ typed tasks via `TaskType` enum with dedicated agents | None — agents run freeform |
| **Prompt registry** | MongoDB-backed, editable, versioned (`registry.txt` seed) | Hardcoded in seed file + code |
| **WebSocket realtime** | Full push-driven task status updates (`/api/ws/events`) | Polling only (planned: WebSocket) |
| **Profile context injection** | CV/position → cache control blocks in prompts | Not present |
| **JSON recovery** | `parse_llm_json()` handles truncated responses | Not present |
| **Rate limiting** | Token bucket with retry/backoff | Not implemented |
| **Default user setup** | First user = admin + activation flow | No admin/activation |
| **Multi-source with fallback** | S2 → OpenAlex fallback pattern | Partial (some sources) |
| **Editable agent prompts** | System prompts stored in DB, editable via UI | Hardcoded in seed file |
| **Skill isolation testing** | N/A (different architecture) | Missing — cannot test skills independently |
| **Output schema enforcement** | Structured JSON output per task type | Null for all skills |
| **Drag-and-drop skill assignment** | N/A | Checkbox list only |

---

## 12. Improvement Roadmap

### P0 — Critical (broken/missing behavior)

1. **Remove `eu-horizon` from Paper Reviewer** — doesn't belong on a paper review agent
2. **Dead code cleanup** — confirm and remove `ReviewAgent` if unused
3. **Auto-default cleanup on seed** — when seeds run, delete or migrate the 4 placeholders

### P1 — High Impact

4. **Add `recommender` seed config** — provide a proper out-of-box recommender
5. **Add `input_schema`/`output_schema` to skills** — enable composability contracts
6. **Show resolved tools in AgentsPage** — display which tools an agent actually gets from its skillset
7. **Add skill isolation endpoint** — `POST /skills/{id}/run` for independent testing

### P2 — Medium

8. **Add `researcher` role → project-manager** — Project Manager should have its own role rather than being a `researcher` variant
9. **Expand `search_papers` tools for Project Manager** — it has `eu-horizon` but no `search_papers`
10. **Add tool definitions endpoint for UI** — `GET /tools` so frontend can show tool descriptions
11. **Add tool-to-skill mapping in SkillsPage** — show which tools a skill unlocks with descriptions

### P3 — Nice to Have

12. **Drag-and-drop skill reordering** — skill priority matters for prompt merging
13. **WebSocket realtime for agent execution** — push status instead of polling
14. **Prompt registry** — editable prompts stored in DB with version history
15. **professor-pal `parse_llm_json` port** — handle malformed LLM JSON output
16. **Agent execution history** — track runs, outputs, tokens per config

---

> End of analysis. This document is intended for AI agents working on the ScholarFlow codebase.
