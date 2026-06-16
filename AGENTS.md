# AGENTS.md

Repo-specific guidance for AI coding agents. Trust this file over `README.md` when they disagree.

## Stack snapshot

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL, LangGraph/LangChain, httpx
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router
- **LLM**: OpenRouter (multi-model), with user-provided API key support
- **External APIs**: Semantic Scholar, arXiv, CrossRef, OpenAlex
- **Auth**: JWT (jose), pbkdf2_sha256 (passlib), per-user API keys Fernet-encrypted
- **Persistence**: PostgreSQL (SQLAlchemy async), Elasticsearch (vector search), MinIO (file storage)
- **Containers**: `docker-compose.yml` — backend (`:8000`), frontend (`:3000`), Elasticsearch, MinIO, PostgreSQL, Redis, Tika

## Commands

```bash
# Backend
uv sync --extra dev
uv run uvicorn app.main:app --reload     # API on :8000

# Frontend (cd frontend)
pnpm install
pnpm dev          # :3000
pnpm build        # tsc && vite build
```

## Architecture

```
academic-pal/
├── backend/
│   ├── app/
│   │   ├── agents/           # LangGraph agents (scholar, reviewer, writer, recommendation)
│   │   ├── api/routes/       # FastAPI routers (auth, chat, tasks, settings, docs)
│   │   ├── services/         # Academic APIs, search, LLM, document processing
│   │   ├── tools/            # LangChain tools (search, citation, document reading)
│   │   ├── core/             # Config, database, security
│   │   ├── models/           # SQLAlchemy models
│   │   └── schemas/          # Pydantic request/response models
│   └── migrations/           # Alembic migrations
├── frontend/
│   └── src/
│       ├── api/              # Axios client, typed endpoints
│       ├── components/       # Shared UI components
│       ├── pages/            # Route pages
│       └── hooks/            # Custom React hooks
└── docker-compose.yml
```

## Agent system

Four LangGraph agents, each with a state graph:

| Agent | Role | Sources used |
|-------|------|--------------|
| `ScholarAgent` | Search papers across academic databases | Semantic Scholar, arXiv, CrossRef, OpenAlex |
| `PaperReviewAgent` | 7-stage paper review pipeline | Semantic Scholar (citations, references) |
| `WritingAgent` | Polish/rewrite academic text | None (LLM-only) |
| `RecommendationAgent` | Recommend papers based on interests | Semantic Scholar, OpenAlex, vector search |

Agents are created via `app/agents/factory.py` using `AGENT_REGISTRY`.

## Academic API sources

| Source | Auth | Rate limits | Key features |
|--------|------|-------------|--------------|
| **Semantic Scholar** | Optional API key | 1000 RPS shared (free), 1 RPS dedicated (key) | Citations, references, recommendations, bulk search |
| **arXiv** | None | 3s between requests | Preprints, full text XML |
| **CrossRef** | Optional Plus token | 50 req/s | DOI metadata, citation counts |
| **OpenAlex** | None (mailto for polite pool) | ~100K/day | 250M+ works, authors, venues, institutions |

API clients live in `app/services/academic_apis.py`. User API keys are stored encrypted in the `user_api_keys` table.

## Auth & multi-tenancy

- JWT (7-day exp, HS256) stored in `localStorage` (`ap_token`/`ap_user`)
- Axios interceptor injects `Bearer` token
- Per-user API keys (Semantic Scholar, OpenAI, OpenRouter) encrypted with Fernet
- Settings API: `GET/POST/DELETE /settings/api-keys`

## Tests

```bash
uv run pytest
```

## Style & quality gates

- Ruff: `target-version="py312"`, `line-length=100`
- Match existing patterns when adding new code

---

## Reference project: professor-pal

`~/Development/professor-pal/` is an older, more mature version of this system. It provides the same core functionality with additional features and a different tech stack. Use it as a reference for patterns, APIs, and agent designs.

### Stack differences

| Layer | professor-pal | academic-pal (this project) |
|-------|---------------|-----------------------------|
| Database | MongoDB (pymongo, 17 collections) | PostgreSQL (SQLAlchemy async) |
| LLM client | Ariadne proxy (Anthropic Claude) | OpenRouter (multi-model) |
| Agent framework | Custom `BaseAgent` + orchestrator | LangGraph state graphs |
| Prompt management | Mongo-backed registry (`registry.txt` seed) | Code-level system prompts |
| Realtime | WebSocket events (`/api/ws/events`) | Polling (planned: WebSocket) |
| Frontend | React 19 + Vite 8 + Tailwind v4 | React 19 + Vite + Tailwind |

### Features in professor-pal not yet in academic-pal

| Feature | Description | Files |
|---------|-------------|-------|
| **SoTA Searcher** | Multi-source literature synthesis with Tavily + S2 + OpenAlex | `backend/agents/sota_searcher.py` |
| **Novelty Assessor** | Scores ideas against existing literature | `backend/agents/novelty_assessor.py` |
| **Venue Recommender** | Suggests journals/conferences per idea | `backend/agents/venue_recommender.py` |
| **Call Recommender** | Finds funding calls (EU Horizon, ERC, national) | `backend/agents/call_recommender.py` |
| **Researcher Tracker** | Periodic updates on tracked researchers | `backend/agents/researcher_tracker.py` |
| **Profile Manager** | Parses CV/position/committee into structured profile | `backend/agents/profile_manager.py` |
| **Document Summarizer** | Background summarization of uploaded docs | `backend/agents/document_summarizer.py` |
| **Inspiration Generator** | Cross-domain ideas seeded by reference papers | `backend/agents/inspiration_generator.py` |
| **Prompt Registry** | Editable prompts stored in MongoDB | `config/prompts/registry.txt`, `backend/prompts.py` |
| **WebSocket realtime** | Push-driven task status updates | `backend/api/realtime.py`, `frontend/src/contexts/RealtimeEvents.tsx` |
| **Multi-user admin** | First user auto-admin, activation flow | `backend/auth.py` |

### Academic APIs used in professor-pal

```python
# backend/tools/academic_apis.py

# Semantic Scholar — with user API key support, rate limiting, retry
class SemanticScholarClient:
    search_papers(query, limit, fields)
    get_paper_details(paper_id)
    search_authors(name, limit)
    get_author_papers(author_id, limit)

# OpenAlex — free, no key, 250M+ works
class OpenAlexClient:
    search_works(query, limit)
    search_authors(name, limit)
    get_author_works(author_id, limit)
    _reconstruct_abstract(inverted_index)  # handles OpenAlex abstract format

# Tavily — AI-optimized web search (optional)
class WebSearchTool:
    search(query, max_results, search_depth)
    search_academic(query)    # adds site:scholar.google.com etc.
    search_funding(query)     # adds site:ec.europa.eu etc.
    search_venues(query)      # adds conference/journal/CFP keywords
```

### Key patterns to adopt from professor-pal

**1. Multi-source search with fallback** (`sota_searcher.py`):
```python
# Try Semantic Scholar first, fall back to OpenAlex
ss_papers = await semantic_scholar.search(topic, limit=max_papers)
if not ss_papers:
    oa_papers = await openalex.search_works(topic, limit=max_papers * 2)
# Deduplicate by title, sort by citation count
```

**2. Partial JSON recovery** (`base.py:parse_llm_json`):
```python
# Handles truncated LLM responses by:
# 1. Stripping code fences
# 2. Trimming to outermost braces
# 3. Closing truncated JSON ("}" / "}}")
# 4. Regex extraction of specific fields
```

**3. Rate limiting with token bucket** (`academic_apis.py`):
```python
# Free tier: 1 request per 3 seconds
# With API key: 1000+ requests per 5 minutes
# Automatic retry with exponential backoff on 429
```

**4. Profile contexts in prompts** (`base.py`):
```python
# Inject academic profile as Anthropic cache_control blocks
# Order matters: prepend new fixed-position contexts in base.py
contexts = self._get_profile_contexts(summaries=summaries)
response = await self.llm.complete(
    system_prompt=self.system_prompt,
    user_message=user_message,
    cached_contexts=contexts,
)
```

**5. Orchestrator dispatch** (`orchestrator.py`):
```python
# Central routing by TaskType enum
match task_type:
    case TaskType.THESIS_IDEAS:
        return await self.research_generator.generate_thesis_ideas(...)
    case TaskType.SOTA_SEARCH:
        return await self.sota_searcher.search_sota(...)
    # ... 20 task types total
```

### Agent list (professor-pal)

| Agent | Task | Description |
|-------|------|-------------|
| `ResearchGeneratorAgent` | `THESIS_IDEAS`, `EU_PROPOSALS`, `NATIONAL_PROPOSALS`, `PHD_PROPOSALS` | Generates research ideas/proposals |
| `InspirationGeneratorAgent` | `INSPIRATION_IDEAS` | Cross-domain ideas from reference papers |
| `NoveltyAssessorAgent` | `NOVELTY_ASSESSMENT` | Scores ideas against literature |
| `ReviewAgent` | `PUBLICATION_REVIEW`, `THESIS_REVIEW`, `GRANT_REVIEW` | Reviews academic work |
| `VenueRecommenderAgent` | `VENUE_RECOMMENDATION` | Suggests journals/conferences |
| `CallRecommenderAgent` | `CALL_RECOMMENDATION` | Finds funding opportunities |
| `VenueRelevanceAssessorAgent` | `VENUE_RELEVANCE` | Scores venue fit |
| `CallRelevanceAssessorAgent` | `CALL_RELEVANCE` | Scores call fit |
| `ProposalCallMatcherAgent` | `PROPOSAL_CALL_MATCH` | Matches proposals to calls |
| `IdeaVenueMatcherAgent` | `IDEA_VENUE_MATCH` | Matches ideas to venues |
| `SotaSearcherAgent` | `SOTA_SEARCH` | Literature synthesis |
| `RelevanceAssessorAgent` | `RELEVANCE_ASSESSMENT` | Reference paper relevance |
| `ResearcherTrackerAgent` | `RESEARCHER_UPDATE` | Tracks researcher activity |
| `ProfileManagerAgent` | `PROFILE_INGEST` | Parses CV/position docs |
| `DocumentSummarizerAgent` | `DOCUMENT_SUMMARY` | Summarizes uploaded docs |

### Collections (MongoDB, professor-pal)

`users`, `academic_profiles`, `research_configurations`, `uploaded_documents`, `publications`, `reference_papers`, `notes`, `generated_ideas`, `reviews`, `sota_reports`, `venue_recommendations`, `call_recommendations`, `proposal_call_matches`, `proposal_venue_matches`, `tracked_researchers`, `researcher_updates`, `assistant_conversations`, plus infrastructure: `task_runs`, `prompt_configs`, `model_configs`, `counters`

### Configuration (professor-pal)

Required env vars (`.env`):
- `PROFESSOR_PAL_ARIADNE_API_KEY` — LLM proxy auth
- `PROFESSOR_PAL_MONGO_URI` — MongoDB connection
- `PROFESSOR_PAL_JWT_SECRET` — JWT signing secret
- `PROFESSOR_PAL_FRONTEND_URL` — CORS origin

Optional:
- `PROFESSOR_PAL_TAVILY_API_KEY` — Web search
- `PROFESSOR_PAL_SEMANTIC_SCHOLAR_API_KEY` — Higher S2 rate limits
