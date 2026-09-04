"""
routers/auth.py
===============
Router FastAPI — authentification unifiée pour users ET admins.

Un seul système d'auth pour tout le monde.
Le rôle (admin/user) est stocké en base et inclus dans la réponse du login.
Le frontend redirige selon le rôle après login.

Endpoints :
  POST /auth/register  → inscription d'un nouvel utilisateur
  POST /auth/login     → login pour tous (user ET admin)
  GET  /auth/me        → identité de l'utilisateur connecté
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from core.dependencies import require_user_token
from database.connection import get_db
from database.crud import create_user, authenticate_user
from database.models import User
from schemas import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inscription d'un nouvel utilisateur",
)
def register(
    credentials: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Crée un nouveau compte utilisateur avec role='user'.
    Le username doit être unique — 409 sinon.
    """
    try:
        user = create_user(db, credentials.username, credentials.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le nom d'utilisateur '{credentials.username}' est déjà pris.",
        )

    logger.info("Nouvel utilisateur inscrit : %s", credentials.username)

    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Connexion — user ou admin",
)
def login(
    credentials: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authentifie un utilisateur et retourne un JWT token.
    Le champ 'role' dans la réponse permet au frontend de rediriger :
      - role='admin' → /admin/dashboard
      - role='user'  → /chat
    Message d'erreur volontairement vague pour éviter l'énumération.
    """
    user = authenticate_user(db, credentials.username, credentials.password)

    if not user:
        logger.warning("Échec de connexion pour : %s", credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=credentials.username)

    logger.info(
        "Connexion réussie : %s (role=%s)",
        credentials.username, user.role,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        username=user.username,
        role=user.role,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Identité de l'utilisateur connecté",
)
def get_me(current_user: User = Depends(require_user_token)) -> UserResponse:
    """
    Route protégée — retourne l'identité de l'utilisateur connecté.
    Utilisée par le frontend au démarrage pour vérifier la session.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
    )

