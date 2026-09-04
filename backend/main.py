"""
main.py
=======
Backend FastAPI — BeHave AI Chatbot
"""

import logging
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from routers.auth import router as auth_router
from routers.admin_documents import router as admin_documents_router
from services.document_service import set_vector_store
from services.file_processor import FileProcessingError, process_uploaded_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
load_dotenv(Path(__file__).parent.parent / ".env")
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "ingestion"))
sys.path.insert(0, str(PROJECT_ROOT / "rag"))

from schemas import (
    ChatResponse,
    ChatCreateRequest,
    ChatRenameRequest,
    ChatItem,
    ChatListResponse,
    HealthResponse,
    HistoryMessage,
    HistoryResponse,
)
from chain import BeHaveRAGChain, _GROQ_MODEL_TEXT
from retriever import BeHaveRetriever
from database.connection import engine, get_db
from database.models import Base, User
from database.crud import (
    create_admin_if_not_exists,
    save_conversation,
    create_chat,
    get_user_chats,
    get_chat_by_id,
    rename_chat,
    delete_chat,
)
from core.dependencies import require_user_token
from backend.admin_config import ADMIN_USERNAME, ADMIN_PASSWORD_HASH

# ---------------------------------------------------------------------------
# Application FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="BeHave AI Assistant",
    description="Assistant conversationnel RAG pour la suite BeHave — Siryos",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_documents_router)

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        create_admin_if_not_exists(
            db=db,
            username=ADMIN_USERNAME,
            password_hash=ADMIN_PASSWORD_HASH,
        )
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Pipeline RAG — retriever partagé entre toutes les sessions
# ---------------------------------------------------------------------------
print("Initialisation du pipeline RAG...")
_shared_retriever = BeHaveRetriever()
set_vector_store(_shared_retriever.store)
print("Pipeline RAG pret !")

sessions: dict[str, BeHaveRAGChain] = {}


def get_or_create_session(session_id: str) -> BeHaveRAGChain:
    """Retourne la session existante ou en crée une nouvelle avec le retriever partagé."""
    if session_id not in sessions:
        sessions[session_id] = BeHaveRAGChain(retriever=_shared_retriever)
    return sessions[session_id]


def _resolve_chat_id(session_id: str, user: User, db: Session) -> int | None:
    """Résout un chat_id valide en DB à partir du session_id, sinon None."""
    try:
        chat_id = int(session_id)
    except (ValueError, TypeError):
        return None

    chat_obj = get_chat_by_id(db, chat_id=chat_id, user_id=user.id)
    return chat_id if chat_obj else None


# ---------------------------------------------------------------------------
# Routes — Gestion des chats
# ---------------------------------------------------------------------------

@app.post("/chats", response_model=ChatItem)
def create_new_chat(
    body:         ChatCreateRequest,
    current_user: User    = Depends(require_user_token),
    db:           Session = Depends(get_db),
):
    """Crée un nouveau chat pour l'utilisateur connecté."""
    chat = create_chat(db, user_id=current_user.id, title=body.title)
    return ChatItem(
        id=chat.id,
        title=chat.title,
        created_at=chat.created_at.isoformat(),
    )


@app.get("/chats", response_model=ChatListResponse)
def list_chats(
    current_user: User    = Depends(require_user_token),
    db:           Session = Depends(get_db),
):
    """Retourne tous les chats de l'utilisateur connecté."""
    chats = get_user_chats(db, user_id=current_user.id)
    return ChatListResponse(
        chats=[
            ChatItem(id=c.id, title=c.title, created_at=c.created_at.isoformat())
            for c in chats
        ],
        total=len(chats),
    )


@app.patch("/chats/{chat_id}", response_model=ChatItem)
def rename_existing_chat(
    chat_id:      int,
    body:         ChatRenameRequest,
    current_user: User    = Depends(require_user_token),
    db:           Session = Depends(get_db),
):
    """Renomme un chat existant."""
    chat = rename_chat(db, chat_id=chat_id, user_id=current_user.id, new_title=body.title)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat introuvable.")
    return ChatItem(id=chat.id, title=chat.title, created_at=chat.created_at.isoformat())


@app.delete("/chats/{chat_id}")
def delete_existing_chat(
    chat_id:      int,
    current_user: User    = Depends(require_user_token),
    db:           Session = Depends(get_db),
):
    """Supprime un chat, ses conversations, ses fichiers indexés et la session en mémoire."""
    session_id = f"{current_user.username}_{chat_id}"
    sessions.pop(session_id, None)
    _shared_retriever.store.delete_temp_chunks(str(chat_id))

    ok = delete_chat(db, chat_id=chat_id, user_id=current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Chat introuvable.")
    return {"message": "Chat supprimé.", "chat_id": chat_id}


# ---------------------------------------------------------------------------
# Routes — Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health_check():
    try:
        doc_count = _shared_retriever.store._collection.count()
        return HealthResponse(
            status="ok",
            chromadb_documents=doc_count,
            model=f"{_GROQ_MODEL_TEXT} (Groq)",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Routes — Chat RAG
# ---------------------------------------------------------------------------

_AUTO_TITLE_MAX_LEN: int = 40


@app.post("/chat", response_model=ChatResponse)
async def chat(
    question:     str              = Form(...),
    session_id:   str              = Form(default="default"),
    files:        list[UploadFile] = File(default=[]),
    current_user: User             = Depends(require_user_token),
    db:           Session          = Depends(get_db),
):
    """
    Reçoit une question et, optionnellement, des fichiers à joindre au chat.

    Les fichiers sont extraits, découpés en chunks et indexés dans la collection
    temporaire ChromaDB (chat_temp_files) sous ce chat_id — mini-RAG. La question
    est ensuite traitée par le RAG, qui cherche d'abord dans ces fichiers avant de
    retomber sur la documentation BeHave.

    Auto-renommage : à la première question d'un chat, le titre est automatiquement
    mis à jour avec les premiers mots de la question.
    """
    if not question.strip():
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")

    chat_id = _resolve_chat_id(session_id, current_user, db)
    full_session_id = f"{current_user.username}_{session_id}"

    if files:
        if chat_id is None:
            raise HTTPException(
                status_code=400,
                detail="Impossible de joindre un fichier : chat introuvable ou invalide.",
            )
        try:
            file_chunks = await process_uploaded_files(files)
        except FileProcessingError as e:
            raise HTTPException(status_code=400, detail=str(e))

        _shared_retriever.store.add_temp_chunks(file_chunks, chat_id=str(chat_id))

    try:
        chain  = get_or_create_session(full_session_id)
        result = chain.ask(question, chat_id=str(chat_id) if chat_id else None)

        save_conversation(
            db=db,
            user_id=current_user.id,
            question=question,
            answer=result["content"],
            module=result.get("module"),
            source=result.get("source"),
            chat_id=chat_id,
        )

        if chat_id and chain.history_turns == 1:
            raw_title  = question.strip()
            auto_title = (
                raw_title[:_AUTO_TITLE_MAX_LEN] + "..."
                if len(raw_title) > _AUTO_TITLE_MAX_LEN
                else raw_title
            )
            rename_chat(
                db,
                chat_id=chat_id,
                user_id=current_user.id,
                new_title=auto_title,
            )

        return ChatResponse(
            answer=result["content"],
            module=result.get("module"),
            source=result.get("source"),
            session_id=full_session_id,
            chunks_used=chain.k,
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Routes — Historique RAG
# ---------------------------------------------------------------------------

@app.get("/history", response_model=HistoryResponse)
def get_history(
    session_id:   str  = "default",
    current_user: User = Depends(require_user_token),
):
    full_session_id = f"{current_user.username}_{session_id}"
    chain = get_or_create_session(full_session_id)
    messages = [
        HistoryMessage(role=msg["role"], content=msg["content"])
        for msg in chain.history
    ]
    return HistoryResponse(
        session_id=full_session_id,
        messages=messages,
        total_messages=len(messages),
    )


@app.delete("/history")
def reset_history(
    session_id:   str  = "default",
    current_user: User = Depends(require_user_token),
):
    """Réinitialise l'historique RAG de la session."""
    full_session_id = f"{current_user.username}_{session_id}"
    chain = get_or_create_session(full_session_id)
    chain.reset_history()
    return {"message": "Historique réinitialisé.", "session_id": full_session_id}