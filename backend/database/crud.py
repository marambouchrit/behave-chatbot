"""
database/crud.py
================
Opérations CRUD sur PostgreSQL.
"""

import logging
from sqlalchemy.orm import Session
from core.security import hash_password, verify_password
from database.models import User, Conversation, Chat, UserRole

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def create_user(
    db: Session,
    username: str,
    password: str,
    role: UserRole = UserRole.user,
) -> User:
    """
    Crée un nouvel utilisateur dans la base.
    Raises ValueError si le username existe déjà.
    """
    if get_user_by_username(db, username):
        raise ValueError(f"Username '{username}' déjà utilisé.")

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Utilisateur créé : %s (role=%s)", username, role)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """
    Vérifie les credentials. Retourne User si valide, None sinon.
    Vérifie toujours le hash pour éviter les timing attacks.
    """
    user = get_user_by_username(db, username)
    dummy_hash = "$2b$12$dummy_hash_for_timing_attack_prevention_only_xx"
    hash_to_check = user.password_hash if user else dummy_hash
    password_ok   = verify_password(password, hash_to_check)

    if not user or not password_ok:
        return None
    return user


def create_admin_if_not_exists(
    db: Session,
    username: str,
    password_hash: str,
) -> None:
    """Crée l'admin en base s'il n'existe pas — idempotent."""
    if get_user_by_username(db, username):
        logger.info("Admin '%s' déjà présent en base.", username)
        return

    user = User(
        username=username,
        password_hash=password_hash,
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()
    logger.info("Admin '%s' créé en base au démarrage.", username)


# ---------------------------------------------------------------------------
# Chats
# ---------------------------------------------------------------------------

def create_chat(
    db: Session,
    user_id: int,
    title: str = "Nouvelle conversation",
) -> Chat:
    """Crée un nouveau chat pour un utilisateur."""
    chat = Chat(user_id=user_id, title=title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    logger.info("Chat créé : id=%d user_id=%d title=%r", chat.id, user_id, title)
    return chat


def get_user_chats(db: Session, user_id: int) -> list[Chat]:
    """Retourne tous les chats d'un utilisateur, plus récents en premier."""
    return (
        db.query(Chat)
        .filter(Chat.user_id == user_id)
        .order_by(Chat.created_at.desc())
        .all()
    )


def get_chat_by_id(db: Session, chat_id: int, user_id: int) -> Chat | None:
    """Retourne un chat par son id, uniquement si il appartient à l'utilisateur."""
    return (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == user_id)
        .first()
    )


def rename_chat(
    db: Session,
    chat_id: int,
    user_id: int,
    new_title: str,
) -> Chat | None:
    """Renomme un chat. Retourne None si le chat n'existe pas ou n'appartient pas à l'user."""
    chat = get_chat_by_id(db, chat_id, user_id)
    if not chat:
        return None
    chat.title = new_title
    db.commit()
    db.refresh(chat)
    return chat


def delete_chat(db: Session, chat_id: int, user_id: int) -> bool:
    """
    Supprime un chat et toutes ses conversations (cascade).
    Retourne True si supprimé, False si introuvable.
    """
    chat = get_chat_by_id(db, chat_id, user_id)
    if not chat:
        return False
    db.delete(chat)
    db.commit()
    logger.info("Chat supprimé : id=%d user_id=%d", chat_id, user_id)
    return True


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

def save_conversation(
    db: Session,
    user_id: int,
    question: str,
    answer: str,
    module: str | None = None,
    source: str | None = None,
    chat_id: int | None = None,
) -> Conversation:
    """Sauvegarde un échange question/réponse en base."""
    conversation = Conversation(
        user_id=user_id,
        chat_id=chat_id,
        question=question,
        answer=answer,
        module=module,
        source=source,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_all_conversations(
    db: Session,
    skip: int = 0,
    limit: int = 50,
) -> list[Conversation]:
    """Retourne toutes les conversations paginées, plus récentes en premier."""
    return (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_conversations_count(db: Session) -> int:
    """Retourne le nombre total de conversations."""
    return db.query(Conversation).count()