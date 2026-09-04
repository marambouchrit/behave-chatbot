from database.connection import Base, engine, get_db
from database.models import User, Conversation, UserRole
from database.crud import (
    get_user_by_username,
    create_user,
    authenticate_user,
    create_admin_if_not_exists,
    save_conversation,
    get_all_conversations,
    get_conversations_count,
)