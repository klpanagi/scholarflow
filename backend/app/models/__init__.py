import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Float, Integer, Enum as SQLEnum, JSON, Table
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import enum

from ..core.database import Base


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class AgentRole(str, enum.Enum):
    RESEARCHER = "researcher"
    WRITER = "writer"
    REVIEWER = "reviewer"
    RECOMMENDER = "recommender"


class Strategy(str, enum.Enum):
    DIRECT = "direct"
    CRITIQUE = "critique"
    REFLECTION = "reflection"
    EVALUATOR_OPTIMIZER = "evaluator_optimizer"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    profile = relationship("AcademicProfile", back_populates="user", uselist=False)
    papers = relationship("Paper", back_populates="owner")
    agent_configs = relationship("AgentConfig", back_populates="user")
    workspaces = relationship("Workspace", back_populates="user")
    api_keys = relationship("UserApiKey", back_populates="user", cascade="all, delete-orphan")


class AcademicProfile(Base):
    __tablename__ = "academic_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    domains = Column(ARRAY(String), default=list)
    interests = Column(ARRAY(String), default=list)
    institutions = Column(ARRAY(String), default=list)
    orcid = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    reading_history = Column(ARRAY(UUID(as_uuid=True)), default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="profile")


class Paper(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    authors = Column(ARRAY(String), default=list)
    abstract = Column(Text, nullable=True)
    doi = Column(String(100), nullable=True, index=True)
    arxiv_id = Column(String(50), nullable=True, index=True)
    year = Column(Integer, nullable=True)
    venue = Column(String(255), nullable=True)
    minio_key = Column(String(500), nullable=False)
    es_doc_id = Column(String(100), nullable=True)
    citations = Column(ARRAY(UUID(as_uuid=True)), default=list)
    tags = Column(ARRAY(String), default=list)
    doc_type = Column(String(50), default="other")
    analysis = Column(JSON, nullable=True)
    embedding = Column(ARRAY(Float), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="papers")
    chunks = relationship("PaperChunk", back_populates="paper", cascade="all, delete-orphan")


class PaperChunk(Base):
    __tablename__ = "asset_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    section = Column(String(100), nullable=True)
    page = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    embedding = Column(ARRAY(Float), nullable=True)
    es_doc_id = Column(String(100), nullable=True)

    paper = relationship("Paper", back_populates="chunks")


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(SQLEnum(AgentRole), nullable=False)
    provider = Column(String(50), nullable=False, default="opencode")
    model = Column(String(100), nullable=False, default="gpt-4o")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    strategy = Column(SQLEnum(Strategy), default=Strategy.DIRECT)
    tools = Column(ARRAY(String), default=list)
    system_prompt = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="agent_configs")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    papers = Column(ARRAY(UUID(as_uuid=True)), default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="workspaces")
    conversations = relationship("Conversation", back_populates="workspace")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    agent_config_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.id"), nullable=True)
    title = Column(String(255), nullable=True)
    strategy_trace = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.timestamp")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    tool_results = Column(JSON, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True)
    file_key = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    prompt_template = Column(Text, nullable=True)
    builtin_tools = Column(ARRAY(String), default=list)
    custom_tools = Column(JSON, nullable=True)
    input_schema = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)
    tags = Column(ARRAY(String), default=list)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


agent_skills_table = Table(
    "agent_skills",
    Base.metadata,
    Column("agent_config_id", UUID(as_uuid=True), ForeignKey("agent_configs.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)


AgentConfig.skills = relationship("Skill", secondary=agent_skills_table, lazy="selectin")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True, default="New Chat")
    model = Column(String(100), nullable=False, default="opencode-1")
    provider = Column(String(50), nullable=False, default="opencode")
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.timestamp")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    file_key = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("ChatSession", back_populates="messages")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    workflow_id = Column(String(100), nullable=False)
    workflow_name = Column(String(255), nullable=False)
    input_text = Column(Text, nullable=True)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    agent_assignments = Column(JSON, nullable=True)
    stages = Column(JSON, nullable=False)
    status = Column(String(50), default="completed")
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    service = Column(String(50), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="api_keys")
