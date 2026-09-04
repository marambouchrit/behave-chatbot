"""
core/security.py
================
Couche de sécurité centrale du projet BeHave Assistant.

Responsabilités :
  - Hacher et vérifier les mots de passe (bcrypt)
  - Créer et décoder les JWT tokens (JSON Web Tokens)
  - Fournir la dépendance FastAPI qui protège les routes admin

Ce module ne fait QUE de la sécurité. Il ne connaît ni les routes,
ni la base de données, ni les schémas métier — principe de responsabilité unique.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer


# Configuration JWT
# Clé secrète utilisée pour SIGNER les tokens.

from admin_config import JWT_SECRET_KEY
SECRET_KEY = JWT_SECRET_KEY

# Algorithme de signature. HS256 (HMAC + SHA-256) est le standard recommandé
# pour les JWT dans les APIs internes.
ALGORITHM = "HS256"

# Durée de vie du token en minutes. Après cette durée, le token expire
# et l'admin devra se reconnecter. 480 min = 8 heures (une journée de travail).
ACCESS_TOKEN_EXPIRE_MINUTES = 480

# ---------------------------------------------------------------------------
# Contexte de hachage des mots de passe
# ---------------------------------------------------------------------------

# CryptContext configure passlib pour utiliser bcrypt.
# bcrypt est intentionnellement LENT (coût computationnel élevé),
# ce qui rend les attaques par force brute très difficiles.
# deprecated="auto" met à jour automatiquement les anciens hashes si besoin.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



# OAuth2PasswordBearer indique à FastAPI que le token JWT doit être fourni
# dans le header Authorization: Bearer <token>.
# tokenUrl pointe vers l'endpoint de login — utilisé uniquement pour
# la documentation Swagger UI, pas pour la logique métier.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login")


# ---------------------------------------------------------------------------
# Fonctions de hachage
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:

    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# Fonctions JWT
# ---------------------------------------------------------------------------

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Le payload est le "contenu" du token.
    # "sub" (subject) est le claim standard JWT pour l'identifiant.
    # "exp" (expiration) est automatiquement vérifié par python-jose lors du décodage.
    payload = {
        "sub": subject,
        "exp": expire,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> str:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré. Veuillez vous reconnecter.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject: str = payload.get("sub")

        if subject is None:
            raise credentials_exception

        return subject

    except JWTError:
        # JWTError couvre : signature invalide, token expiré, format incorrect
        raise credentials_exception


# ---------------------------------------------------------------------------
# Dépendance FastAPI (Dependency Injection)
# ---------------------------------------------------------------------------

def require_admin_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dépendance FastAPI qui protège les routes réservées à l'admin.

    Returns:
        str : username de l'admin authentifié
    """
    return _decode_token(token)