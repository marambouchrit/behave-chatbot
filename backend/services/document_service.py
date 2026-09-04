"""
services/document_service.py
=============================
Couche métier pour la gestion des documents BeHave.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 
# Chemins du projet


_PROJECT_ROOT     = Path(__file__).parent.parent.parent
_INGESTION_DIR    = _PROJECT_ROOT / "ingestion"

UPLOAD_DIR        = _PROJECT_ROOT / "data" / "uploaded_docs"
ORIGINAL_DOCS_DIR = _PROJECT_ROOT / "data" / "documents"
_CHROMA_DB_DIR    = str(_PROJECT_ROOT / "data" / "chroma_db")

_ALLOWED_EXTENSIONS: frozenset = frozenset({".pdf", ".docx",  ".txt" })
_MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024



if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from document_loader import load_document
from chunker import chunk_document
from embedder import BeHaveVectorStore

# ---------------------------------------------------------------------------
# Instance partagée du vector store — chargée UNE SEULE FOIS au démarrage
#
# Pourquoi un singleton module-level ?
#   BeHaveVectorStore charge all-MiniLM-L6-v2 à l'instanciation (~1s).
#   Si on crée une nouvelle instance à chaque appel API, on recharge
#   le modèle à chaque upload/liste/suppression — lent et inutile.
#   Un singleton module-level est la solution la plus simple en Python :
#   le module n'est importé qu'une seule fois, donc l'instance aussi.
# ---------------------------------------------------------------------------

_vector_store: Optional[BeHaveVectorStore] = None

def set_vector_store(store: BeHaveVectorStore) -> None:
    """
    Injecte l'instance BeHaveVectorStore déjà créée par le pipeline RAG.
    Évite de recharger le modèle d'embedding une deuxième fois au démarrage.
    """
    global _vector_store
    _vector_store = store
    logger.info("Vector store partagé injecté depuis le pipeline RAG.")

def get_vector_store() -> BeHaveVectorStore:
   
    global _vector_store

    if _vector_store is None:
        logger.info("Initialisation du vector store (premier appel)...")
        _vector_store = BeHaveVectorStore(persist_directory=_CHROMA_DB_DIR)

    return _vector_store


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_file(filename: str, file_size: int) -> Optional[str]:
    """
    Valide l'extension et la taille du fichier.
    Retourne un message d'erreur si invalide, None si valide.
    """
    suffix = Path(filename).suffix.lower()

    if suffix not in _ALLOWED_EXTENSIONS:
        return (
            f"Format '{suffix}' non supporté. "
            f"Formats acceptés : {', '.join(_ALLOWED_EXTENSIONS)}"
        )

    if file_size > _MAX_FILE_SIZE_BYTES:
        max_mb = _MAX_FILE_SIZE_BYTES / (1024 * 1024)
        return f"Fichier trop volumineux. Taille maximale : {max_mb:.0f} Mo"

    return None


# ---------------------------------------------------------------------------
# Opérations fichiers disque
# ---------------------------------------------------------------------------

def _ensure_upload_dir() -> None:
    """Crée le dossier d'upload s'il n'existe pas."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_file_to_disk(filename: str, content: bytes) -> Path:
    """
    Sauvegarde le fichier uploadé dans UPLOAD_DIR.

    Returns:
        Path : chemin absolu du fichier sauvegardé
    """
    _ensure_upload_dir()
    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(content)
    logger.info(f"Fichier sauvegardé : {file_path} ({len(content)} octets)")
    return file_path


def delete_file_from_disk(filename: str) -> bool:
    """
    Supprime un fichier du dossier d'upload.

    Returns:
        bool : True si supprimé, False si introuvable
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        logger.warning(f"Fichier introuvable pour suppression : {file_path}")
        return False

    file_path.unlink()
    logger.info(f"Fichier supprimé du disque : {file_path}")
    return True


# ---------------------------------------------------------------------------
# Pipeline d'ingestion
# ---------------------------------------------------------------------------

def index_document(file_path: Path) -> int:
    """
    Pipeline complet : load_document() → chunk_document() → add_documents()
    Même logique que run_indexation.py, appliquée à un seul fichier.

    Returns:
        int : nombre de chunks indexés
    """
    logger.info(f"Début d'indexation : {file_path.name}")

    # Étape 1 — Chargement (load_docx ou load_pdf selon extension)
    document = load_document(str(file_path))

    if not document.page_content.strip():
        raise ValueError(f"Le document '{file_path.name}' est vide ou illisible.")

    # Enrichissement des métadonnées avant chunking
    # chunk_document() les propage automatiquement dans chaque chunk
    document.metadata["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    document.metadata["origin"]      = "admin_upload"

    # Étape 2 — Chunking
    chunks = chunk_document(document)

    if not chunks:
        raise ValueError(f"Aucun chunk généré pour '{file_path.name}'.")

    logger.info(f"Chunks générés : {len(chunks)}")

    # Étape 3 — Embedding + stockage ChromaDB via l'instance partagée
    get_vector_store().add_documents(chunks)

    logger.info(f"Indexation terminée : {file_path.name} — {len(chunks)} chunks")
    return len(chunks)


def delete_document_from_index(filename: str) -> int:
    """
    Supprime tous les chunks d'un document de ChromaDB.
    Utilise la méthode publique delete_by_source() — pas d'accès à _collection.

    Returns:
        int : nombre de chunks supprimés
    """
    logger.info(f"Suppression de l'index pour : {filename}")
    return get_vector_store().delete_by_source(filename)


# ---------------------------------------------------------------------------
# Listing des documents indexés
# ---------------------------------------------------------------------------

def list_indexed_documents() -> list[dict]:
    """
    Retourne la liste des documents distincts indexés dans ChromaDB,
    avec leur nombre de chunks et leur taille sur disque.
    Utilise la méthode publique get_all_metadatas() — pas d'accès à _collection.
    """
    metadatas = get_vector_store().get_all_metadatas()

    if not metadatas:
        return []

    docs: dict[str, dict] = {}

    for meta in metadatas:
        source = meta.get("source", "inconnu")

        if source not in docs:
            docs[source] = {
                "filename":     source,
                "chunks_count": 0,
                "uploaded_at":  meta.get("uploaded_at", "N/A"),
                "file_size_kb": _get_file_size_kb(source),
            }

        docs[source]["chunks_count"] += 1

    return list(docs.values())


def _get_file_size_kb(filename: str) -> float:
    """
    Retourne la taille d'un fichier en Ko.
    Cherche dans UPLOAD_DIR puis dans ORIGINAL_DOCS_DIR.
    Retourne 0.0 si introuvable.
    """
    for directory in (UPLOAD_DIR, ORIGINAL_DOCS_DIR):
        file_path = directory / filename
        if file_path.exists():
            return round(file_path.stat().st_size / 1024, 2)

    return 0.0