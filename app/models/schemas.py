import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    error: str | None = None
    n_pages: int
    n_chunks: int

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    document_id: uuid.UUID
    status: str
    celery_state: str | None = None
    error: str | None = None


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    provider: Literal["hosted", "ollama"] = "hosted"
    top_k: int = Field(5, ge=1, le=20)
    rerank: bool = True
    document_ids: list[uuid.UUID] | None = None


class CitationOut(BaseModel):
    ref: int
    document_id: uuid.UUID
    filename: str
    page: int
    text: str
    score: float


class ChatOut(BaseModel):
    answer: str
    provider: str
    model: str
    citations: list[CitationOut]
    retrieval_ms: float
    generation_ms: float
    prompt_tokens: int
    completion_tokens: int
