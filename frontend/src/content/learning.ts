// =============================================================================
// Learning section content — single source of truth for the /learning routes
// =============================================================================
//
// This file is intentionally JSX-free: it holds typed data, a Zod schema, and
// a small set of helpers. The actual pages in `src/pages/learning/*` consume
// this data and decide how to render it.
//
// Word counts drive the `readingMinutes` for each section. If you change the
// prose, update the matching entry in `WORD_COUNTS` (or recompute via the
// `countWords` helper at the bottom of this file).
// =============================================================================

import { z } from 'zod'

// -----------------------------------------------------------------------------
// Lucide icon name (string literal type)
// -----------------------------------------------------------------------------
//
// Components render the icon dynamically by name to keep this file free of
// React/JSX. Keep this in sync with the `icon` prop in `lucide-react`.
export const LUCIDE_ICON_NAMES = [
  'FileText',
  'Sparkles',
  'Users',
  'Swords',
  'ScrollText',
  'Settings2',
  'GraduationCap',
  'BookOpen',
] as const

export type LucideIconName = (typeof LUCIDE_ICON_NAMES)[number]

// -----------------------------------------------------------------------------
// Difficulty
// -----------------------------------------------------------------------------
export const DIFFICULTIES = ['Beginner', 'Intermediate', 'Advanced'] as const
export type Difficulty = (typeof DIFFICULTIES)[number]

// -----------------------------------------------------------------------------
// Reading-time derivation
// -----------------------------------------------------------------------------
//
// Reading speed assumed: 200 words per minute. Minutes are rounded up and
// clamped to a minimum of 1. The map below is the authoritative source of
// truth for the word count of each section; tweak it (and the prose) together.
export const WORDS_PER_MINUTE = 200

export const WORD_COUNTS: Readonly<Record<string, number>> = {
  assets: 820,
  cult: 700,
  roles: 1214,
  strategies: 1107,
  skills: 811,
  configs: 801,
}

/**
 * Convert a word count into a reading-time in minutes.
 * @param slug       Section slug — included in the error message only.
 * @param textWords  Number of words in the section's prose.
 */
export function computeReadingMinutes(slug: string, textWords: number): number {
  if (!Number.isFinite(textWords) || textWords < 0) {
    throw new Error(
      `[learning] computeReadingMinutes: textWords must be a non-negative number (got ${textWords} for slug "${slug}")`,
    )
  }
  return Math.max(1, Math.ceil(textWords / WORDS_PER_MINUTE))
}

/** Whitespace-separated word count for a prose string. */
export function countWords(text: string): number {
  return text.trim().length === 0 ? 0 : text.trim().split(/\s+/).length
}

// -----------------------------------------------------------------------------
// Content block schemas (discriminated union)
// -----------------------------------------------------------------------------
export const textBlockSchema = z.object({
  type: z.literal('text'),
  content: z.string().min(1),
})

export const diagramBlockSchema = z.object({
  type: z.literal('diagram'),
  diagramId: z.string().regex(/^[a-z0-9-]+$/, 'diagramId must be URL-safe (lowercase, digits, hyphens)'),
  caption: z.string().min(1),
})

export const listBlockSchema = z.object({
  type: z.literal('list'),
  items: z
    .array(
      z.object({
        label: z.string().min(1),
        description: z.string().min(1),
        icon: z.string().optional(),
      }),
    )
    .min(1),
})

export const calloutBlockSchema = z.object({
  type: z.literal('callout'),
  variant: z.enum(['info', 'tip', 'warning']),
  title: z.string().min(1),
  content: z.string().min(1),
})

export const contentBlockSchema = z.discriminatedUnion('type', [
  textBlockSchema,
  diagramBlockSchema,
  listBlockSchema,
  calloutBlockSchema,
])

export type ContentBlock = z.infer<typeof contentBlockSchema>
export type TextBlock = z.infer<typeof textBlockSchema>
export type DiagramBlock = z.infer<typeof diagramBlockSchema>
export type ListBlock = z.infer<typeof listBlockSchema>
export type CalloutBlock = z.infer<typeof calloutBlockSchema>

// -----------------------------------------------------------------------------
// Section schema
// -----------------------------------------------------------------------------
export const learningSectionSchema = z.object({
  id: z.string().regex(/^[a-z0-9-]+$/, 'id must be URL-safe (lowercase, digits, hyphens)'),
  slug: z.string().regex(/^[a-z0-9-]+$/, 'slug must be URL-safe (lowercase, digits, hyphens)'),
  title: z.string().min(1),
  description: z.string().min(1),
  icon: z.enum(LUCIDE_ICON_NAMES),
  difficulty: z.enum(DIFFICULTIES),
  readingMinutes: z.number().int().positive(),
  sections: z.array(contentBlockSchema).min(3).max(10),
})

export type LearningSection = z.infer<typeof learningSectionSchema>

// -----------------------------------------------------------------------------
// Content — section 1: Assets
// -----------------------------------------------------------------------------
//
// Beginner-friendly walkthrough of the document ingestion pipeline:
// upload → object storage → text extraction → chunking → vector index → LLM.
const ASSETS_BLOCKS: ContentBlock[] = [
  {
    type: 'text',
    content:
      'Assets are the raw inputs that flow into ScholarFlow: research papers, reference PDFs, grant proposals, and other long-form documents you upload or import. Every asset is normalised into a canonical representation so that the downstream agents — reviewers, debaters, writers — can reason over it without ever needing to re-parse the original file. The pipeline is designed to be idempotent: re-uploading the same PDF will reuse the existing chunks and embeddings rather than recomputing them from scratch, and a content-hash key is used to detect duplicate uploads so that no work is wasted.',
  },
  {
    type: 'text',
    content:
      'Once an asset is registered, the system runs a five-stage ingestion pipeline. Each stage is owned by a dedicated service so that failures are isolated and observable. The stages are deterministic and versioned, which means you can replay an upload against a newer extraction model and diff the resulting embeddings without losing the original metadata. Every stage emits a structured event that lands in the workflow event log, giving you a full audit trail from the original upload request down to the final embedding vector.',
  },
  {
    type: 'list',
    items: [
      {
        label: 'Upload',
        description:
          'The browser streams the file in chunks to the FastAPI backend, which stores the original binary in MinIO under a per-user key and returns a stable asset_id.',
        icon: 'Upload',
      },
      {
        label: 'Object storage',
        description:
          'MinIO holds the immutable original. The bucket layout separates drafts, published assets, and intermediate extracts so that lifecycle rules can be applied per-class.',
        icon: 'Database',
      },
      {
        label: 'Text extraction',
        description:
          'GROBID (when available) parses the PDF into TEI XML, preserving section structure, figure captions, and bibliographic entries. A regex-based fallback handles non-PDF or malformed inputs.',
        icon: 'FileSearch',
      },
      {
        label: 'Chunking',
        description:
          'Extracted text is split into overlapping windows (default 512 tokens with 64-token overlap) keyed to the document’s section structure so that context survives the cut.',
        icon: 'Scissors',
      },
      {
        label: 'Vector indexing',
        description:
          'Each chunk is embedded with the configured embedding model and written to Elasticsearch alongside the source metadata for hybrid retrieval (BM25 + kNN).',
        icon: 'Search',
      },
    ],
  },
  {
    type: 'text',
    content:
      'Storage and retrieval are deliberately separated. MinIO owns the byte-level truth: the original PDF never changes, even if the extracted text or embeddings are later recomputed. Elasticsearch owns the searchable truth: every chunk is stored with the document’s title, authors, year, section path, and the asset_id that links back to the MinIO object. This split lets you delete a derived index, regenerate it from the original, and re-attach it without touching user data.',
  },
  {
    type: 'text',
    content:
      'Lifecycle rules on the storage layer keep the cost predictable. Drafts are kept for 30 days after the last modification; published assets are retained indefinitely; intermediate extracts (the TEI XML, the raw embeddings before re-ranking) are pruned on a rolling 7-day window. The pruning job is idempotent and emits a summary event so that you can audit what was discarded. If you need a frozen copy of an asset for reproducibility — for example, before re-running a review against a new model version — you can pin it and the lifecycle rules will skip it.',
  },
  {
    type: 'diagram',
    diagramId: 'asset-pipeline',
    caption:
      'Asset ingestion flow — from upload through embedding, with the user’s storage, processing, and retrieval layers side by side.',
  },
  {
    type: 'callout',
    variant: 'tip',
    title: 'Supported formats',
    content:
      'PDF is the primary path. DOCX, TXT, and Markdown are accepted as plain-text fallbacks; scanned PDFs without OCR will produce empty chunks and should be pre-processed with an OCR tool before upload. For very large documents (over 200 pages) we recommend splitting at chapter boundaries before upload — the chunker will respect section boundaries, but a single 800-page thesis will produce an unwieldy number of chunks and slow down downstream retrieval.',
  },
  {
    type: 'text',
    content:
      'Best practices for working with assets come down to three rules. First, name your files well at upload time: the original filename is preserved as a search field, and a file called `paper_v3_FINAL.pdf` is harder to find than `smith-2024-routing-protocols.pdf`. Second, prefer the original PDF over a re-print or a scan: re-prints lose metadata, and scans lose the text layer that GROBID depends on for accurate figure and table extraction. Third, pin the asset before any high-stakes operation — a review that is started against a specific asset version will continue to see the same chunks even if the asset is later re-ingested against a newer extraction model. Pinning is cheap, reversible, and the only way to make a long-running review reproducible.',
  },
  {
    type: 'text',
    content:
      'When a review goes wrong, the asset is usually the first place to look. A common failure mode is that a paper was uploaded as a scan and the chunks are empty or garbage; the agent will then produce a review that is fluent but unrelated to the actual content. Another common mode is that the wrong version of the paper was uploaded — typically an early preprint that the authors have since revised — and the review reads the older claims as if they were current. Both of these are caught by the asset’s content-hash key, which is exposed in the asset detail view and can be cross-checked against the version of record on the publisher’s site. Treat the asset view as the source of truth for what the agents are actually reading, and use the deletion-and-re-upload flow to reset the asset if you suspect corruption — the new upload will be content-hash-keyed, so no work is duplicated.',
  },
]

// -----------------------------------------------------------------------------
// Content — section 2: The Cult
// -----------------------------------------------------------------------------
//
// Explains the "Cult" namespace: the intelligence layer that wires agents,
// skills, chat, and the workflow engine into a single research surface.
const CULT_BLOCKS: ContentBlock[] = [
  {
    type: 'text',
    content:
      '“The Cult” is the internal name for ScholarFlow’s intelligence layer — the set of services and conventions that turn a generic LLM into a research assistant. It is not a single component; it is the wiring that connects the chat surface, the agent registry, the skill store, and the workflow engine into a coherent research experience. The same wiring serves a single user typing a question and a fully orchestrated multi-agent pipeline that takes hours to complete — both share the same primitives, differ only in how they compose them.',
  },
  {
    type: 'text',
    content:
      'In the frontend, the Cult lives behind the `/cult` route group. Pages under that prefix are authenticated, share a common AppShell, and have access to the same real-time task pipeline. From the user’s point of view, the Cult is the place where typed requests become orchestrated runs, where skills are loaded into an agent’s context, and where the results land back in the chat as structured cards. The routing convention is deliberate: anything under `/cult` is the intelligence surface, and anything outside it is a chrome concern (settings, account, billing) that does not need agent access.',
  },
  {
    type: 'text',
    content:
      'The workflow engine at the heart of the Cult is built on LangGraph. Every agent run is a state machine: nodes are agent invocations or tool calls, edges are conditional transitions, and the entire graph is checkpointed after every step. That means a long-running review can be paused, replayed, or branched from any intermediate state — the engine is the source of truth, not the in-memory state of any single process. The chat surface subscribes to the same event stream, so the user sees progress as it happens rather than waiting for a final response that may never arrive.',
  },
  {
    type: 'list',
    items: [
      {
        label: 'Agent registry',
        description:
          'A typed map from role name (e.g. reviewer, writer) to concrete agent class. The factory in `backend/app/agents/factory.py` is the single source of truth.',
        icon: 'Network',
      },
      {
        label: 'Skill store',
        description:
          'Per-user collections of reusable prompt fragments and tool bindings. Skills are injected into an agent’s system prompt at run time.',
        icon: 'Library',
      },
      {
        label: 'Chat surface',
        description:
          'Streaming response UI with tool-call transparency. The chat is a thin client over the same workflow events the agents emit.',
        icon: 'MessagesSquare',
      },
      {
        label: 'Workflow engine',
        description:
          'A LangGraph state machine that sequences stages (e.g. scholar → reviewer → debater → writer) and persists every transition for replay and debugging.',
        icon: 'Workflow',
      },
    ],
  },
  {
    type: 'diagram',
    diagramId: 'cult-architecture',
    caption:
      'Cult architecture — the four moving parts (agents, skills, chat, workflow) and the events that flow between them.',
  },
  {
    type: 'callout',
    variant: 'info',
    title: 'Why “Cult”?',
    content:
      'The name is a nod to the project’s predecessor and to the idea that the most useful AI systems are ensembles of small, well-tuned rituals — system prompts, tools, and post-processing — composed with discipline. There is no central model; there is a cult of small practices, and the value comes from the composition rather than any single component.',
  },
  {
    type: 'text',
    content:
      'The event stream that ties the four moving parts together is implemented as an append-only log, not a message queue. Every transition in the workflow engine emits an event, every tool call emits an event, and every agent invocation emits a start and end event with the full input and output payloads. The chat surface subscribes to a filtered view of the stream (only events relevant to the current conversation), while the workflow detail view subscribes to the unfiltered stream. This is why a long-running review can be paused, replayed, or branched from any intermediate state: the log is the source of truth, and the engine can reconstruct any prior state by replaying events from the start. Retention is configurable per user, with a default of 30 days for the unfiltered stream and 7 days for the chat-filtered stream.',
  },
  {
    type: 'text',
    content:
      'Debugging the Cult is a matter of subscribing to the right slice of the event log. The most useful view is the per-task timeline, which shows the ordered events for a single agent run, with each event clickable to reveal the full input and output payloads. From there you can jump to the prior stage’s events to see what was passed in, or to the next stage’s events to see what was produced. The timeline is also the only place where failed events are visible — a tool call that timed out, an LLM call that was rejected, a schema validation that failed — and each failure has a structured error code that points to the relevant section of the documentation. When in doubt, start with the timeline and work outwards.',
  },
]

// -----------------------------------------------------------------------------
// Content — section 3: Agent Roles
// -----------------------------------------------------------------------------
//
// The 9 specialised roles + the 3 debater variants. This is the largest
// section because users need enough context to pick the right role per task.
const ROLES_BLOCKS: ContentBlock[] = [
  {
    type: 'text',
    content:
      'ScholarFlow ships with nine specialised agent roles. Each role maps to a concrete class in the backend registry, which means the name you see in the UI corresponds to a single, versioned implementation rather than a free-form prompt. Picking the right role is the first step in getting a useful answer: the same question phrased as “find me related work” and “review my methodology” is handled by entirely different agents with different tools, prompts, and output schemas. The roles are deliberately orthogonal to each other — they overlap where collaboration makes sense, and they diverge where a single answer would be misleading.',
  },
  {
    type: 'text',
    content:
      'Roles are not user personas. They are capability bundles — a system prompt, a default strategy, a tool whitelist, and an output schema. When you assign a role to a task, you are saying “use this combination of capabilities, and reject the rest”. This is why the same LLM provider can power all nine roles without any per-role fine-tuning. The capabilities are constraints, not skills: a reviewer will not be tempted to fabricate a citation, because its tool whitelist does not include the search tool, and its output schema does not have a field for one.',
  },
  {
    type: 'text',
    content:
      'Choosing the right role at the start of a task is the single highest-leverage decision you can make. A wrong role will produce a fluent but useless answer, because the model is confident in its capability set even when it is the wrong one. If you are unsure, work backwards from the output schema: what would the perfect answer look like, and which role produces that shape? Researcher produces structured search results; reviewer produces a critique with scores; writer produces long-form prose; revision produces a diff against the original manuscript. Once the output is clear, the role is usually obvious.',
  },
  {
    type: 'list',
    items: [
      {
        label: 'researcher',
        description:
          'Searches the academic literature via Semantic Scholar, arXiv, CrossRef, and OpenAlex. Returns structured results with metadata, abstracts, and citation links.',
        icon: 'Search',
      },
      {
        label: 'writer',
        description:
          'Produces long-form academic prose — paper sections, cover letters, response letters. Honours IMRaD, citation style, and the target venue’s tone.',
        icon: 'PenLine',
      },
      {
        label: 'reviewer',
        description:
          'Critiques a manuscript against the standard review dimensions (novelty, soundness, clarity, reproducibility) and emits a 1–5 score per axis.',
        icon: 'ClipboardCheck',
      },
      {
        label: 'deep_reviewer',
        description:
          'Runs the seven-stage review pipeline — intake, structure, claims, grounding, methodology, red team, synthesis — for high-stakes reviews.',
        icon: 'Microscope',
      },
      {
        label: 'recommender',
        description:
          'Suggests papers, venues, and calls based on a user’s reading history and stated interests. Uses vector search over the user’s library.',
        icon: 'Sparkles',
      },
      {
        label: 'revision',
        description:
          'Takes a manuscript and a reviewer’s comments and produces a point-by-point revision plan with concrete diffs.',
        icon: 'RefreshCw',
      },
      {
        label: 'manager',
        description:
          'Coordinates multi-agent workflows: assigns subtasks, aggregates results, and escalates when agents disagree.',
        icon: 'KanbanSquare',
      },
      {
        label: 'debater',
        description:
          'Runs adversarial debates between pro and con positions on a paper claim. Three variants are available (see callout).',
        icon: 'Swords',
      },
      {
        label: 'review_writer',
        description:
          'Synthesises raw review notes, debate outcomes, and Scholar findings into a polished, editorial-ready Response to Authors and Response to Editor.',
        icon: 'FileSignature',
      },
    ],
  },
  {
    type: 'text',
    content:
      'The roles compose naturally. A typical paper review flow starts with a researcher gathering related work, hands the result to a deep_reviewer for the seven-stage analysis, then to a debater (DEEP variant) for the adversarial stress test, and finally to a review_writer for the editorial synthesis. None of the intermediate stages need to know about the others — each role receives its inputs and emits its outputs in a stable schema, and the workflow engine stitches them together. This is why a failure in any one stage can be retried in isolation, and why a future role can be slotted into the same flow without disturbing the others.',
  },
  {
    type: 'diagram',
    diagramId: 'role-graph',
    caption:
      'Role graph — which agents read from the same sources, which write to the same sinks, and where the manager sits in the orchestration topology.',
  },
  {
    type: 'callout',
    variant: 'info',
    title: 'Debater variants',
    content:
      'The DEBATER role is the only one with three runtime variants. SIMPLE produces a single-pass stress test; STANDARD runs a pro/con debate and synthesises a balanced assessment; DEEP executes a four-stage adversarial pipeline with explicit paper defence, defence evaluation, and a structured final verdict. Pick the variant that matches the stakes: SIMPLE for triage, DEEP for high-impact reviews. The variant is a runtime parameter on the same agent class, not a separate role — it changes the structure of the debate but not the type of output you receive.',
  },
  {
    type: 'text',
    content:
      'Role composition patterns are worth memorising because they cover most realistic research workflows. The first pattern is the search-then-review chain: RESEARCHER gathers related work and passes the structured results to REVIEWER or DEEP_REVIEWER, which can cite the related work by paper id without ever re-searching. The second pattern is the debate-then-revise chain: DEBATER (DEEP variant) stress-tests a manuscript, REVISION produces a diff against the original, and REVIEW_WRITER drafts a Response to Authors that addresses each debated point. The third pattern is the recommend-then-explain chain: RECOMMENDER proposes a venue, and a WRITER configuration bound to the eu-horizon or response-to-editor skill produces a one-paragraph justification that the user can paste into a cover letter. All three patterns compose without modification because every role’s output schema is a strict subset of every other role’s input schema.',
  },
  {
    type: 'text',
    content:
      'When a role fails, the failure usually has a specific signature that points to the cause. A REVIEWER that returns generic praise usually means the manuscript is in the wrong language or the chunks are empty — the reviewer has nothing to critique and falls back to boilerplate. A WRITER that returns repetitive prose usually means the system prompt is too long and the model is ignoring the later sections — bind fewer skills or move the foundational skill to a higher priority. A DEBATER that returns an unbalanced verdict usually means the pro and con positions were seeded with the same evidence — check that the prior stage produced a real disagreement before invoking the debater. All three signatures are diagnosable from the role’s output alone, which is why the output schema is a strict interface rather than a free-form response.',
  },
  {
    type: 'text',
    content:
      'Future roles will be added through the same registry mechanism, with no changes to the workflow engine or the chat surface. A new role is a class that extends the base agent, an entry in the `AGENT_REGISTRY` map, and a system prompt that fits the role’s purpose. The schema validation in the learning page ensures that the new role is documented in plain language before it ships, so users can discover it through the Learning section rather than learning about it from a failed invocation. This is why role documentation lives in code, in the seed file, and in the Learning page — three independent sources that all need to agree before a new role is considered production-ready. The page you are reading is itself a contract: every role mentioned here must exist in the registry, and every role in the registry must be mentioned here, in plain language, with a stable slug that downstream pages can link to.',
  },
  {
    type: 'text',
    content:
      'A useful exercise is to read this section with the workflow detail view open and trace a real review from start to finish. You will see the RESEARCHER emit a search event, the DEEP_REVIEWER emit seven stage events in sequence, the DEBATER emit the four stages of its variant, and the REVIEW_WRITER emit the final synthesis. Each event is timestamped, has a stable id, and carries the full payload. If you can read the timeline and predict which role emitted which event, you understand the role system. If you can read the timeline and predict which strategy shaped the agent’s reasoning, you understand the strategy system. The two are orthogonal: roles describe what was done, strategies describe how it was done.',
  },
]

// -----------------------------------------------------------------------------
// Content — section 4: Agent Strategies
// -----------------------------------------------------------------------------
//
// The 4 reasoning strategies from the Strategy enum. These are independent
// of the role: every role can run under any strategy.
const STRATEGIES_BLOCKS: ContentBlock[] = [
  {
    type: 'text',
    content:
      'A strategy is the reasoning pattern an agent uses to turn a prompt into a final answer. Roles describe what an agent does; strategies describe how it thinks. Every role can be run under any of the four strategies defined in the `Strategy` enum, which means the same writer can be invoked as a direct drafter (DIRECT) or as a self-critical reviser (EVALUATOR_OPTIMIZER) without changing its tools or its role-specific prompt. Strategies are pure orchestration patterns: the LLM is the same, the system prompt is the same, the only thing that changes is the loop that the workflow engine runs around the call.',
  },
  {
    type: 'text',
    content:
      'Choosing a strategy is a cost-vs-quality trade-off. DIRECT is the cheapest and the fastest; EVALUATOR_OPTIMIZER is the most expensive because it runs the model multiple times. For routine operations — formatting a citation, summarising a known document — DIRECT is the right default. For ambiguous, high-stakes operations — drafting a response to reviewers, scoring a manuscript — a more elaborate strategy pays for itself in fewer downstream corrections. The cost ratio between DIRECT and EVALUATOR_OPTIMIZER on a typical task is roughly 1:8, so the bar for escalating should be high and the evaluation should be empirical: if the same DIRECT call fails on three different inputs, it is time to escalate.',
  },
  {
    type: 'text',
    content:
      'Strategies also interact with role choice in subtle ways. A REVIEWER run under CRITIQUE produces a structured critique-then-revise cycle, which is ideal for a draft that the user wants to iterate on. A REVIEWER run under REFLECTION produces a more honest assessment of the manuscript’s limitations, which is more useful for a final recommendation. A WRITER run under EVALUATOR_OPTIMIZER can produce publishable prose on the first invocation, but only when the rubric is concrete enough to score against — abstract rubrics like “sound academic prose” will loop forever. Always pair your strategy choice with an objective success criterion, otherwise the loop will not know when to stop.',
  },
  {
    type: 'list',
    items: [
      {
        label: 'direct',
        description:
          'Single-pass: the model receives the prompt and returns the final answer in one shot. Fastest and cheapest. Best for deterministic transforms and well-scoped tasks.',
        icon: 'Zap',
      },
      {
        label: 'critique',
        description:
          'Generates a draft, then runs a second pass that critiques the draft against the original requirements and produces a revised answer. Doubles the cost, halves the obvious errors.',
        icon: 'MessageSquareWarning',
      },
      {
        label: 'reflection',
        description:
          'Generates a draft, reflects on its own assumptions and gaps, and produces a second, more honest draft. Useful for tasks where the model is likely to overstate certainty.',
        icon: 'Reflection',
      },
      {
        label: 'evaluator_optimizer',
        description:
          'Iterative loop: a generator produces a candidate, an evaluator scores it against a rubric, and the loop continues until the score converges or a budget is exhausted. The most expensive but the most reliable.',
        icon: 'IterationCw',
      },
    ],
  },
  {
    type: 'diagram',
    diagramId: 'strategy-flow',
    caption:
      'Strategy flow — the four reasoning patterns and the points at which each one adds a new model call to the critical path.',
  },
  {
    type: 'callout',
    variant: 'tip',
    title: 'Choosing a strategy',
    content:
      'Start with DIRECT and only escalate when you see a recurring failure mode. REFLECTION is often the right second choice for tasks where the model is confidently wrong; CRITIQUE is the right second choice for tasks where the model is too verbose; EVALUATOR_OPTIMIZER is reserved for tasks with an objective score (e.g. structured review, rubric-based grading). When in doubt, run a few DIRECT calls in parallel and compare — if the answers agree, DIRECT is sufficient; if they diverge, you have empirical evidence that a more elaborate strategy will help.',
  },
  {
    type: 'text',
    content:
      'Latency budgets should be set explicitly per strategy. DIRECT runs in a single model call and typically completes in 2-8 seconds for short outputs, 15-30 seconds for long-form prose. CRITIQUE doubles the call count and runs in roughly 2x the latency of DIRECT. REFLECTION has the same call count as CRITIQUE but the reflection pass tends to be longer than the critique pass, so the latency is typically 2.5-3x DIRECT. EVALUATOR_OPTIMIZER is unbounded in the worst case — set an explicit budget (in seconds, in tokens, or in iterations) and abort the loop when the budget is exhausted, otherwise a poorly-tuned rubric will run forever. The default budget is 3 iterations, which is enough for most well-defined rubrics and short enough to bound the worst case.',
  },
  {
    type: 'text',
    content:
      'Strategies also affect how retries interact with the workflow engine. A DIRECT run that fails is cheap to retry — the model is non-deterministic but the failure mode is usually obvious (a parse error, a refusal, a token limit). A CRITIQUE run that fails is more expensive to retry because the second pass can fail for reasons the first pass did not. A REFLECTION run that fails often fails in the reflection pass, which means the retry should use a different system prompt to break the failure mode. An EVALUATOR_OPTIMIZER run that fails almost always fails in the evaluator, and the retry should reset the evaluator’s rubric state to avoid a stuck loop. The workflow engine has built-in retry policies for each strategy that you can override per configuration, but the defaults are tuned for the common case. The engine emits a `strategy.retry` event for every retry, so the timeline will show the original failure, the retry decision, and the eventual outcome — use that to tune the policy for your own workload.',
  },
  {
    type: 'text',
    content:
      'A common mistake is to assume a more elaborate strategy is always better. It is not: a CRITIQUE run on a task where the model already has high confidence will produce a worse answer than a DIRECT run, because the critique pass introduces noise that the model did not need. The right way to choose is to instrument the task, run a small batch under DIRECT, and measure the quality against a ground truth. If the DIRECT quality is high (close to the ground truth), DIRECT is the right choice. If it is mediocre, escalate to CRITIQUE. If CRITIQUE is still mediocre, escalate to REFLECTION. Only reach for EVALUATOR_OPTIMIZER when the task has an objective rubric and the cost of a bad answer is high enough to justify the extra latency. Treat the strategy choice as a hyperparameter to be tuned, not a default to be set once and forgotten, and keep a small log of strategy-vs-quality measurements so that the choice is empirical rather than aesthetic.',
  },
  {
    type: 'text',
    content:
      'Finally, remember that strategies compose with skills. A REVIEWER configuration bound to the solo-paper-review skill under DIRECT produces a fast, single-pass review that is well-suited to triage. The same configuration under CRITIQUE produces a slower review that catches more subtle methodological issues, at the cost of doubling the token spend. The same configuration under EVALUATOR_OPTIMIZER, with a rubric that scores the review on a 1-10 scale per dimension, produces the most thorough review the system is capable of — at roughly 8x the cost of the DIRECT version. The rubric itself becomes the source of quality control, and the workflow engine can be configured to require a minimum rubric score before accepting a review as final.',
  },
]

// -----------------------------------------------------------------------------
// Content — section 5: Default Skills
// -----------------------------------------------------------------------------
//
// The 10 seeded skills. Names match the keys in the backend skill table
// exactly — do not rename without updating `scholarflow_skills.py`.
const SKILLS_BLOCKS: ContentBlock[] = [
  {
    type: 'text',
    content:
      'Skills are reusable prompt fragments that inject domain expertise into an agent. They are not tools: a skill changes how an agent reasons, not what it can call. A skill is a name, a short description, a long prompt template, an optional list of built-in tools, and a tag set for discoverability. When an agent runs, every skill bound to it is concatenated into its system prompt in a stable order — the order is the order in which the skills were bound to the configuration, and it is preserved across runs to keep the system prompt byte-identical between invocations of the same configuration.',
  },
  {
    type: 'text',
    content:
      'ScholarFlow ships with ten default skills. They cover the most common research workflows — writing, reviewing, grant drafting, project management — and are seeded into every new user’s library on first login. The seed list is the canonical source; the names below are the exact keys used in the database and must not be renamed casually. The skills are also tagged for discoverability: tags like `horizon-europe`, `peer-review`, `literature`, and `project-management` are indexed so that the skill picker can recommend the right skill for a given task. Tag matches are exact, not fuzzy, so tag taxonomy is a deliberate design decision.',
  },
  {
    type: 'text',
    content:
      'Skill composition follows a small set of rules that are worth understanding before you bind skills to a configuration. First, skills are concatenated in binding order, so put foundational skills (writing, citation style) before specialised ones (Horizon Europe, response-to-author). Second, a skill can reference another skill by name in its prompt template, and the engine will inline the referenced skill at load time. Third, a skill that declares a built-in tool adds that tool to the agent’s tool whitelist for the duration of the run — the tool is not added to the configuration’s permanent whitelist. These rules keep skill composition predictable and make it possible to reason about a configuration’s effective prompt without running it.',
  },
  {
    type: 'list',
    items: [
      {
        label: 'eu-horizon',
        description:
          'Horizon Europe expertise: programme structure, funding instruments, evaluation criteria, Part B conventions, TRL, Open Science, ethics.',
        icon: 'Landmark',
      },
      {
        label: 'academic-writing',
        description:
          'IMRaD structure, citation practices, publication strategy, and scientific communication across disciplines and venues.',
        icon: 'BookOpen',
      },
      {
        label: 'project-management',
        description:
          'WBS, Gantt charts, deliverables, milestones, risk management, RACI matrices, and EU reporting conventions.',
        icon: 'ListChecks',
      },
      {
        label: 'solo-paper-review',
        description:
          'Standalone seven-stage paper review pipeline with search tools. For autonomous reviews without a Scholar Agent.',
        icon: 'FileSearch',
      },
      {
        label: 'paper-review',
        description:
          'Workflow-integrated paper evaluation. Pure assessment — no search tools, uses Scholar Agent output from the prior stage.',
        icon: 'ClipboardList',
      },
      {
        label: 'paper-review-analyze',
        description:
          'Analysis stages of a paper-review workflow — enables structured citation extraction via GROBID for SearchAgent and ReviewAgent.',
        icon: 'ScanSearch',
      },
      {
        label: 'paper-review-write',
        description:
          'Writing stages of a paper-review workflow — used by DebateAgent and ReviewWriterAgent for synthesising text-based review output.',
        icon: 'FilePen',
      },
      {
        label: 'literature-review',
        description:
          'Systematic literature review methodology — search strategy, source selection, PRISMA flow, synthesis writing, gap identification.',
        icon: 'Library',
      },
      {
        label: 'response-to-author',
        description:
          'Conventions for the public Response to Authors review document. Tone: professional, respectful, constructive. Includes bracket identifiers and required section ordering.',
        icon: 'Mail',
      },
      {
        label: 'response-to-editor',
        description:
          'Conventions for the confidential Response to Editor note. Tone: direct, candid, concise. Includes blocking/non-blocking concern flags.',
        icon: 'Mails',
      },
    ],
  },
  {
    type: 'diagram',
    diagramId: 'skill-loading',
    caption:
      'Skill loading — how skill prompt templates and tool bindings are merged into an agent’s system prompt at run time.',
  },
  {
    type: 'callout',
    variant: 'info',
    title: 'Custom skills',
    content:
      'Users can create additional skills scoped to their own library. Custom skills follow the same schema as the defaults but can be edited, versioned, and bound to specific agent configurations. Custom skills are not visible to other users unless explicitly published. A published skill becomes part of the public catalogue and can be adopted by other users; the original author retains attribution but the public version is immutable. Forking a public skill creates a new private skill that starts from the same template but diverges on first edit.',
  },
  {
    type: 'text',
    content:
      'Designing effective skills is a skill in itself. The strongest skills are short, declarative, and contain only what the model would not already know. A skill that explains IMRaD structure is good — every model benefits from a reminder. A skill that explains your group’s specific section conventions is also good, because no model has that information. A skill that re-states the model’s general capabilities is bad — it burns tokens without changing behaviour. A skill that contains example dialogues is occasionally useful as a few-shot prompt, but the examples should be chosen for their diversity, not their volume. The best skills fit in a single screen, contain 5-15 structural rules, and end with a short “do not” list to keep the model from overgeneralising.',
  },
  {
    type: 'text',
    content:
      'Skill versioning is supported at the database level, not the application level. Each save of a skill creates a new version row, and the binding to a configuration stores a reference to a specific version, not to a skill name. This means a configuration always runs against the exact prompt template it was bound to, even if the skill is later updated. To roll a new skill version out to existing configurations, you must explicitly re-bind the configuration. The default behaviour on skill update is to leave existing bindings untouched and only new bindings pick up the latest version, which is the right default for production but can be confusing when you are iterating on a skill in development.',
  },
]

// -----------------------------------------------------------------------------
// Content — section 6: Agent Configurations
// -----------------------------------------------------------------------------
//
// 14 configs total: 7 seeded (from `scholarflow_skills.py`) + 7 defaults
// (from `agents.py`). Names match the database values exactly.
const CONFIGS_BLOCKS: ContentBlock[] = [
  {
    type: 'text',
    content:
      'An agent configuration binds a role, a provider, a model, a strategy, a system prompt, and a set of skill bindings into a single reusable record. Configurations are the unit of personalisation: rather than passing a long tuple of arguments to every agent invocation, you select a named configuration and the backend reconstructs the full execution context from it. Configurations are per-user and can be cloned, edited, or marked as default. They are also the only place where the binding between a skill and a role is persisted, so editing a configuration is the only way to change which skills a given role has access to.',
  },
  {
    type: 'text',
    content:
      'ScholarFlow seeds fourteen configurations for every new user: seven from the ScholarFlow skill seed file (specialised configs for grant workflows) and seven from the agents route’s default list (general-purpose baselines for every role). Together they cover every role in the registry, including all three DEBATER variants, and they are designed to be cloned and customised rather than edited in place. The seed and default lists are deliberately complementary: the seed list covers the high-stakes grant workflows with specialised prompts and skill bindings, while the default list provides a general-purpose baseline for every role that you can clone to start a custom configuration.',
  },
  {
    type: 'text',
    content:
      'Configuration resolution at run time is a single SQL query plus a template merge. The backend loads the configuration by id, fetches the bound skills in order, concatenates their prompt templates into the role’s base system prompt, instantiates the agent class from the role key, and configures the LLM client with the provider and model. The whole process is cached for the duration of a single run, so re-using a configuration across many tasks is essentially free. Cloning a configuration is the recommended way to experiment: the clone becomes your personal default and the original is left untouched.',
  },
  {
    type: 'list',
    items: [
      {
        label: 'Proposal Writer',
        description:
          'WRITER role, DIRECT strategy. Specialised for Horizon Europe proposal drafting. Skills: eu-horizon, academic-writing.',
        icon: 'FileText',
      },
      {
        label: 'Proposal Reviewer',
        description:
          'REVIEWER role, CRITIQUE strategy. Scores proposals against Excellence, Impact, Implementation. Skills: eu-horizon, solo-paper-review.',
        icon: 'ClipboardCheck',
      },
      {
        label: 'Project Manager',
        description:
          'MANAGER role, DIRECT strategy. Designs WPs, Gantt charts, risk registers, and budget justifications. Skills: eu-horizon, project-management.',
        icon: 'KanbanSquare',
      },
      {
        label: 'Review Writer',
        description:
          'REVIEW_WRITER role, DIRECT strategy. Synthesises raw review notes into Response to Authors and Response to Editor. Skills: response-to-author, response-to-editor.',
        icon: 'FileSignature',
      },
      {
        label: 'Simple Debater',
        description:
          'DEBATER role (SIMPLE variant), CRITIQUE strategy. Single-pass stress test. Skills: none.',
        icon: 'Swords',
      },
      {
        label: 'Standard Debater',
        description:
          'DEBATER role (STANDARD variant), CRITIQUE strategy. Pro/con debate with balanced synthesis. Skills: none.',
        icon: 'Swords',
      },
      {
        label: 'Deep Debater',
        description:
          'DEBATER role (DEEP variant), CRITIQUE strategy. Four-stage adversarial pipeline with explicit paper defence. Skills: none.',
        icon: 'Swords',
      },
      {
        label: 'Default Researcher',
        description:
          'RESEARCHER role, DIRECT strategy. General-purpose literature search baseline.',
        icon: 'Search',
      },
      {
        label: 'Default Writer',
        description:
          'WRITER role, DIRECT strategy. General-purpose long-form academic writing baseline.',
        icon: 'PenLine',
      },
      {
        label: 'Default Reviewer',
        description:
          'REVIEWER role, CRITIQUE strategy. Standard four-dimension peer review baseline.',
        icon: 'ClipboardCheck',
      },
      {
        label: 'Default Recommender',
        description:
          'RECOMMENDER role, DIRECT strategy. Personalised paper and venue recommendation baseline.',
        icon: 'Sparkles',
      },
      {
        label: 'Default Review Writer',
        description:
          'REVIEW_WRITER role, DIRECT strategy. General-purpose synthesis of review notes and Scholar findings.',
        icon: 'FileSignature',
      },
      {
        label: 'Default Debater',
        description:
          'DEBATER role, CRITIQUE strategy. Balanced general-purpose debate baseline (no variant pinning).',
        icon: 'Swords',
      },
      {
        label: 'Default Deep Reviewer',
        description:
          'DEEP_REVIEWER role, CRITIQUE strategy. Seven-stage review pipeline baseline.',
        icon: 'Microscope',
      },
    ],
  },
  {
    type: 'diagram',
    diagramId: 'config-flow',
    caption:
      'Configuration resolution — how a config_id is expanded into a runnable agent instance at invocation time.',
  },
  {
    type: 'callout',
    variant: 'warning',
    title: 'Don’t edit the seeds in place',
    content:
      'Seeded configurations are re-applied on every login via a diff-based upsert. Edits to a seeded config will be overwritten the next time the seed runs. To customise, clone the seed and edit the clone — the clone becomes your personal default and is never overwritten. The same rule applies to the seven default configurations from the agents route: they are also upserted, so direct edits are lost on the next login. If you want to track changes to a configuration, clone it first and use the version history on the clone.',
  },
  {
    type: 'text',
    content:
      'Configuration management in production follows a small set of conventions that are worth adopting early. First, never edit a seeded configuration in place — clone it and give the clone a meaningful name that reflects the workflow it supports (e.g. `Proposal Writer v2 — MSCA PF`). Second, when you find a configuration that works well, mark it as default so that new conversations and shortcuts point to it without manual selection. Third, use the version history to track meaningful changes; cosmetic edits do not need a new version, but changes to the system prompt, the bound skills, or the model should always be versioned. Fourth, retire configurations you no longer use — the configuration picker is only useful if it is short enough to scan, and an unmaintained configuration is worse than no configuration at all. The four conventions together turn a configuration library from a list of free-form prompts into a versioned, named, discoverable set of capabilities that survives team turnover and model upgrades.',
  },
]

// -----------------------------------------------------------------------------
// Sections — assembled list
// -----------------------------------------------------------------------------
export const learningSections = [
  {
    id: 'assets',
    slug: 'assets',
    title: 'Assets',
    description:
      'How papers, PDFs, and references are ingested and prepared for AI analysis.',
    icon: 'FileText' as LucideIconName,
    difficulty: 'Beginner' as Difficulty,
    readingMinutes: computeReadingMinutes('assets', WORD_COUNTS.assets),
    sections: ASSETS_BLOCKS,
  },
  {
    id: 'cult',
    slug: 'cult',
    title: 'The Cult',
    description:
      'The intelligence layer — agents, skills, chat, and the workflow engine that powers research.',
    icon: 'Sparkles' as LucideIconName,
    difficulty: 'Beginner' as Difficulty,
    readingMinutes: computeReadingMinutes('cult', WORD_COUNTS.cult),
    sections: CULT_BLOCKS,
  },
  {
    id: 'roles',
    slug: 'roles',
    title: 'Agent Roles',
    description:
      'The 9 specialized agent roles that power ScholarFlow’s automated research.',
    icon: 'Users' as LucideIconName,
    difficulty: 'Intermediate' as Difficulty,
    readingMinutes: computeReadingMinutes('roles', WORD_COUNTS.roles),
    sections: ROLES_BLOCKS,
  },
  {
    id: 'strategies',
    slug: 'strategies',
    title: 'Agent Strategies',
    description:
      'The 4 reasoning strategies that shape how agents think, debate, and refine their work.',
    icon: 'Swords' as LucideIconName,
    difficulty: 'Advanced' as Difficulty,
    readingMinutes: computeReadingMinutes('strategies', WORD_COUNTS.strategies),
    sections: STRATEGIES_BLOCKS,
  },
  {
    id: 'skills',
    slug: 'skills',
    title: 'Default Skills',
    description:
      'The 10 built-in skills that inject domain expertise into agents.',
    icon: 'ScrollText' as LucideIconName,
    difficulty: 'Intermediate' as Difficulty,
    readingMinutes: computeReadingMinutes('skills', WORD_COUNTS.skills),
    sections: SKILLS_BLOCKS,
  },
  {
    id: 'configs',
    slug: 'configs',
    title: 'Agent Configurations',
    description:
      'The 14 seeded and default agent configurations you can customize or extend.',
    icon: 'Settings2' as LucideIconName,
    difficulty: 'Intermediate' as Difficulty,
    readingMinutes: computeReadingMinutes('configs', WORD_COUNTS.configs),
    sections: CONFIGS_BLOCKS,
  },
] as const satisfies ReadonlyArray<LearningSection>

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

/**
 * Look up a learning section by its URL slug.
 *
 * Returns `undefined` if the slug does not match any registered section.
 */
export function getSectionBySlug(slug: string): LearningSection | undefined {
  return learningSections.find((s) => s.slug === slug)
}

/**
 * All slugs in the order they appear in `learningSections`.
 * Useful for navigation, routing, and sitemap generation.
 */
export const LEARNING_SECTION_SLUGS = learningSections.map((s) => s.slug) as readonly string[]

/**
 * All section IDs. Same order as `learningSections`.
 */
export const LEARNING_SECTION_IDS = learningSections.map((s) => s.id) as readonly string[]
