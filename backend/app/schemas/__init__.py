from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: UUID
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class AcademicProfileBase(BaseModel):
    domains: list[str] = []
    interests: list[str] = []
    institutions: list[str] = []
    orcid: Optional[str] = None
    bio: Optional[str] = None


class AcademicProfileCreate(AcademicProfileBase):
    pass


class AcademicProfileUpdate(AcademicProfileBase):
    pass


class AcademicProfileResponse(AcademicProfileBase):
    id: UUID
    user_id: UUID
    reading_history: list[UUID] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaperBase(BaseModel):
    title: str
    authors: list[str] = []
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    tags: list[str] = []


class PaperCreate(PaperBase):
    pass


class PaperResponse(PaperBase):
    id: UUID
    owner_id: UUID
    minio_key: str
    es_doc_id: Optional[str] = None
    citations: list[UUID] = []
    doc_type: str = "other"
    analysis: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaperListResponse(BaseModel):
    items: list[PaperResponse]
    total: int
    page: int
    size: int


class PaperSearchResult(BaseModel):
    paper: PaperResponse
    score: float
    highlights: dict[str, list[str]] = {}


class AgentConfigBase(BaseModel):
    name: str
    role: str
    provider: str = "opencode"
    model: str = "gpt-4o"
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(4096, ge=1, le=128000)
    strategy: str = "direct"
    tools: list[str] = []
    system_prompt: Optional[str] = None
    is_default: bool = False
    variant: Optional[str] = None

    @field_validator("variant")
    @classmethod
    def validate_variant(cls, v):
        if v is not None and v not in {"simple", "standard", "deep"}:
            raise ValueError("variant must be one of: 'simple', 'standard', 'deep'")
        return v


class AgentConfigCreate(AgentConfigBase):
    pass


class AgentConfigUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    strategy: Optional[str] = None
    tools: Optional[list[str]] = None
    system_prompt: Optional[str] = None
    is_default: Optional[bool] = None
    variant: Optional[str] = None


class AgentConfigResponse(AgentConfigBase):
    id: UUID
    user_id: UUID
    skills: list["SkillResponse"] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceBase(BaseModel):
    name: str
    description: Optional[str] = None
    papers: list[UUID] = []


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    papers: Optional[list[UUID]] = None


class WorkspaceResponse(WorkspaceBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    agent_config_id: Optional[UUID] = None
    title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    tool_calls: Optional[dict] = None
    tool_results: Optional[dict] = None
    extra_metadata: Optional[dict] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None
    agent_config_id: Optional[UUID] = None
    workspace_id: UUID


class ScholarSearchRequest(BaseModel):
    query: str
    limit: int = Field(10, ge=1, le=100)
    sources: list[str] = ["semantic_scholar", "arxiv", "openalex"]
    year_from: Optional[int] = None
    year_to: Optional[int] = None


class ScholarPaperResponse(BaseModel):
    title: str
    authors: list[str]
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    url: Optional[str] = None
    source: str


class AgentRunRequest(BaseModel):
    agent_type: str
    agent_config_id: Optional[UUID] = None
    model: Optional[str] = None
    strategy: Optional[str] = "direct"
    message: str
    context: Optional[dict] = None
    thread_id: Optional[str] = None


class AgentRunResponse(BaseModel):
    output: str
    metadata: dict = {}


class AgentListResponse(BaseModel):
    agents: list[dict]


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    agent_config_id: Optional[UUID] = None


class MessageCreate(BaseModel):
    content: str
    extra_metadata: Optional[dict] = None


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"
    model: str = "opencode-1"               # retained for backward compat; copied from agent
    provider: str = "opencode"              # retained for backward compat
    system_prompt: Optional[str] = None
    agent_config_id: UUID                                    # REQUIRED
    asset_ids: list[UUID] = []                              # OPTIONAL

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    system_prompt: Optional[str] = None
    agent_config_id: Optional[UUID] = None


class ChatSessionResponse(BaseModel):
    id: UUID
    title: Optional[str]
    model: str
    provider: str
    system_prompt: Optional[str]
    agent_config_id: Optional[UUID]                         # nullable for legacy rows
    asset_ids: list[UUID] = []                              # convenience for client
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentConfigSummary(BaseModel):
    """Lightweight agent config for the chat agent picker."""
    id: UUID
    name: str
    role: str
    provider: str
    model: str
    is_default: bool
    variant: Optional[str] = None


class ChatSessionAgentInfo(BaseModel):
    """Agent config + attached assets returned by the stream call."""
    agent: AgentConfigSummary
    assets: list["PaperResponse"]
    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str
    parent_message_id: Optional[UUID] = None


class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    file_key: Optional[str] = None
    file_name: Optional[str] = None
    parent_message_id: Optional[UUID] = None
    extra_metadata: Optional[dict] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ChatForkRequest(BaseModel):
    from_message_id: UUID
    title: Optional[str] = None


class ChatFileUploadResponse(BaseModel):
    file_key: str
    file_name: str


class CustomToolDefinition(BaseModel):
    name: str
    description: str
    endpoint: str
    method: str = "GET"
    headers: Optional[dict] = None
    params_schema: Optional[dict] = None
    response_parser: Optional[str] = None


class SkillBase(BaseModel):
    name: str
    description: Optional[str] = None
    prompt_template: Optional[str] = None
    builtin_tools: list[str] = []
    custom_tools: list[CustomToolDefinition] = []
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    tags: list[str] = []
    is_public: bool = False


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt_template: Optional[str] = None
    builtin_tools: Optional[list[str]] = None
    custom_tools: Optional[list[CustomToolDefinition]] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    tags: Optional[list[str]] = None
    is_public: Optional[bool] = None


class SkillResponse(SkillBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentConfigUpdateWithSkills(BaseModel):
    skill_ids: list[UUID] = []


class WorkflowExecutionResponse(BaseModel):
    id: UUID
    workflow_id: str
    workflow_name: str
    input_text: Optional[str] = None
    paper_id: Optional[UUID] = None
    agent_assignments: Optional[dict] = None
    stages: list[dict]
    status: str
    duration_seconds: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowExecutionListResponse(BaseModel):
    items: list[WorkflowExecutionResponse]
    total: int


class RevisionSessionCreate(BaseModel):
    workflow_execution_id: UUID
    agent_config_id: Optional[UUID] = None
    title: Optional[str] = None


class RevisionSessionResponse(BaseModel):
    id: UUID
    workflow_execution_id: UUID
    user_id: UUID
    agent_config_id: Optional[UUID] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RevisionMessageCreate(BaseModel):
    content: str


class RevisionMessageResponse(BaseModel):
    id: UUID
    revision_session_id: UUID
    role: str
    content: str
    extra_metadata: Optional[dict] = None
    file_key: Optional[str] = None
    file_name: Optional[str] = None
    parent_message_id: Optional[UUID] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class RevisionFileUploadResponse(BaseModel):
    file_key: str
    file_name: str


from .workflow_event import ExecutionEvent, WorkflowEventResponse, WorkflowSnapshotResponse  # noqa: E402,F401


class WorkflowExecutionSnapshotResponse(BaseModel):
    events: list[ExecutionEvent]
    execution: WorkflowExecutionResponse
