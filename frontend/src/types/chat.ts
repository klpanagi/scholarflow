/**
 * Chat types — mirrors Phase 2 backend schema (snake_case for response types,
 * camelCase for input params). Kept separate from useChat.ts to keep hooks lean.
 */

// ---------------------------------------------------------------------------
// Agent roles & labels
// ---------------------------------------------------------------------------

/** All agent roles the backend supports. */
export type AgentRole =
  | 'researcher'
  | 'writer'
  | 'reviewer'
  | 'recommender'
  | 'revision'
  | 'manager'
  | 'debater'
  | 'deep_reviewer'
  | 'review_writer'

/** Human-readable labels for each agent role. */
export const ROLE_LABELS: Record<AgentRole, string> = {
  researcher: 'Researcher',
  writer: 'Writer',
  reviewer: 'Reviewer (Simple)',
  deep_reviewer: 'Reviewer (Deep — 7-stage)',
  debater: 'Debater',
  recommender: 'Recommender',
  manager: 'Manager',
  revision: 'Revision',
  review_writer: 'Review Writer',
}

// ---------------------------------------------------------------------------
// Chat session
// ---------------------------------------------------------------------------

/**
 * Mirrors `ChatSessionResponse` from the backend.
 *
 * Field names use **snake_case** to match the API response directly — no
 * transformation needed when the response is stored in state.
 */
export interface ChatSession {
  id: string
  title: string | null
  model: string
  provider: string
  system_prompt: string | null
  /** Agent config UUID — `null` on legacy sessions created before Phase 2. */
  agent_config_id: string | null
  /** Paper/asset UUIDs attached to this session. */
  asset_ids: string[]
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Create-session params (input)
// ---------------------------------------------------------------------------

/**
 * Parameters for creating a new chat session.
 *
 * Uses **camelCase** because this is a TypeScript input type, not a raw API
 * response. The hook translates these to snake_case before POSTing.
 */
export interface CreateSessionParams {
  /** Required — the agent config to use for this session. */
  agentConfigId: string
  /** Optional model override (copied from the agent config on the backend if omitted). */
  model?: string
  /** Optional provider override (copied from the agent config on the backend if omitted). */
  provider?: string
  /** Optional session title. */
  title?: string
  /** Optional system prompt override. */
  systemPrompt?: string
  /** Optional paper/asset UUIDs to attach. */
  assetIds?: string[]
}

// ---------------------------------------------------------------------------
// Chat message
// ---------------------------------------------------------------------------

/**
 * Mirrors `ChatMessageResponse` from the backend.
 */
export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  file_key?: string | null
  file_name?: string | null
  parent_message_id?: string | null
  extra_metadata?: Record<string, unknown> | null
  timestamp: string
}

// ---------------------------------------------------------------------------
// Agent config (for the picker / agent list)
// ---------------------------------------------------------------------------

/**
 * Mirrors `AgentConfigResponse` from the backend.
 * Used by the `useAgentConfigs` hook.
 */
export interface AgentConfig {
  id: string
  name: string
  role: string
  provider: string
  model: string
  temperature: number
  max_tokens: number
  strategy: string
  variant: string | null
  tools: string[]
  system_prompt: string | null
  is_default: boolean
  skills: {
    id: string
    name: string
    description: string | null
    builtin_tools: string[]
  }[]
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Asset / Paper summary (for the asset picker)
// ---------------------------------------------------------------------------

/**
 * Mirrors `PaperResponse` from the backend.
 * Used by the `useAssetLibrary` hook.
 */
export interface AssetSummary {
  id: string
  title: string
  authors: string[]
  abstract: string | null
  doi: string | null
  arxiv_id: string | null
  year: number | null
  venue: string | null
  tags: string[]
  doc_type: string
  created_at: string
  updated_at: string
}

/**
 * Paginated response from `GET /assets/`.
 * Mirrors `PaperListResponse` from the backend.
 */
export interface AssetListResponse {
  items: AssetSummary[]
  total: number
  page: number
  size: number
}
