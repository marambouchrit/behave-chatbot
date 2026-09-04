"""
schemas.py
==========
Modèles Pydantic pour la validation des données API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatCreateRequest(BaseModel):
    """Corps de POST /chats"""
    title: str = Field(default="Nouvelle conversation", max_length=200)


class ChatRenameRequest(BaseModel):
    """Corps de PATCH /chats/{chat_id}"""
    title: str = Field(..., min_length=1, max_length=200)


class ChatItem(BaseModel):
    """Un chat dans la liste GET /chats"""
    id:         int
    title:      str
    created_at: str

    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    """Réponse de GET /chats"""
    chats: List[ChatItem]
    total: int


# ---------------------------------------------------------------------------
# Messages / RAG
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Corps de la requête POST /chat"""
    question: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    answer: str
    module: Optional[str] = None
    source: Optional[str] = None
    session_id: str
    chunks_used: int


class HistoryMessage(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[HistoryMessage]
    total_messages: int


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    chromadb_documents: int
    model: str


# ---------------------------------------------------------------------------
# Documents admin
# ---------------------------------------------------------------------------

class DocumentInfo(BaseModel):
    filename: str = Field(..., description="Nom du fichier")
    chunks_count: int = Field(..., description="Nombre de chunks indexés")
    uploaded_at: str = Field(..., description="Date d'indexation ISO 8601")
    file_size_kb: float = Field(..., description="Taille en Ko")


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
    total_documents: int


class DocumentUploadResponse(BaseModel):
    filename: str
    chunks_indexed: int
    message: str
    success: bool = True


class DocumentDeleteResponse(BaseModel):
    filename: str
    chunks_deleted: int
    message: str
    success: bool = True


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)


class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class TokenResponse(BaseModel):
    access_token:       str
    token_type:         str = "bearer"
    expires_in_minutes: int
    username:           str
    role:               str


class UserResponse(BaseModel):
    id:       int
    username: str
    role:     str


# ---------------------------------------------------------------------------
# Historique admin
# ---------------------------------------------------------------------------

class ConversationRecord(BaseModel):
    id:         int
    username:   str
    question:   str
    answer:     str
    module:     Optional[str]
    source:     Optional[str]
    created_at: str


class HistoryPageResponse(BaseModel):
    conversations: List[ConversationRecord]
    total:         int
    skip:          int
    limit:         int