# admin_config.py
from dotenv import load_dotenv
import os

load_dotenv()

# JWT — utilisé pour TOUS les utilisateurs (admin ET user)
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")

# Admin — utilisé uniquement au premier démarrage pour créer l'admin en base
ADMIN_USERNAME: str      = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH: str = os.getenv("ADMIN_PASSWORD_HASH", "")

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "")

if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY manquante dans .env")
if not ADMIN_PASSWORD_HASH:
    raise ValueError("ADMIN_PASSWORD_HASH manquante dans .env")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL manquante dans .env")