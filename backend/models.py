from enum import Enum
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class GrantStatus(str, Enum):
    DISCOVERED = "discovered"
    REVIEWING = "reviewing"
    APPLIED = "applied"
    AWARDED = "awarded"
    REJECTED = "rejected"
    NOT_ELIGIBLE = "not_eligible"


class Grant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    funder: str
    description: str
    url: Optional[str] = None
    deadline: Optional[str] = None
    max_amount: Optional[int] = None
    min_amount: Optional[int] = None
    focus_areas: str = "[]"  # JSON array stored as string
    status: GrantStatus = GrantStatus.DISCOVERED
    eligibility_notes: Optional[str] = None
    application_notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SearchJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    focus_areas: str = "[]"  # JSON array
    status: str = "pending"  # pending, running, complete, failed
    current_phase: Optional[str] = None
    phases_done: str = "[]"   # JSON list of completed phase names
    grants_found: int = 0
    searches_made: int = 0
    log_entries: str = "[]"   # JSON list of {ts, msg, level}
    error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None


class ApplicationSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    grant_id: int = Field(foreign_key="grant.id")
    messages: str = "[]"  # JSON array of {role, content}
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Request/response schemas (not DB tables)
class GrantUpdate(SQLModel):
    status: Optional[GrantStatus] = None
    application_notes: Optional[str] = None
    eligibility_notes: Optional[str] = None
    deadline: Optional[str] = None


class SearchRequest(SQLModel):
    focus_areas: list[str] = [
        "tree planting",
        "rewilding",
        "solar energy",
        "insulation",
        "heat pumps",
        "biodiversity",
        "community education",
        "electric vehicles",
        "net zero",
    ]


class ChatMessage(SQLModel):
    role: str
    content: str


class ChatRequest(SQLModel):
    grant_id: int
    session_id: Optional[int] = None
    message: str
