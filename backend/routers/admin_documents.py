"""
routers/admin_documents.py
===========================
Router FastAPI pour la gestion des documents BeHave par l'admin.


Toutes les routes sont protégées par require_admin_token.
La logique métier est déléguée à services/document_service.py.
Ce router ne fait que :
  - Valider les entrées HTTP
  - Appeler le service
  - Retourner la réponse HTTP appropriée
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from core.security import require_admin_user
from services.document_service import (
    validate_file,
    save_file_to_disk,
    index_document,
    list_indexed_documents,
    delete_document_from_index,
    delete_file_from_disk,
)
from schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentInfo,
    DocumentDeleteResponse,
)

from database.connection import get_db
from database.crud import get_all_conversations, get_conversations_count
from schemas import HistoryPageResponse, ConversationRecord
from sqlalchemy.orm import Session
from database.models import User
logger = logging.getLogger(__name__)



# Regex pour nettoyer les noms de fichiers — on garde uniquement
# les caractères alphanumériques, tirets, underscores et points.
# Cela prévient les path traversal attacks (ex: "../../etc/passwd.pdf")
_SAFE_FILENAME_PATTERN = re.compile(r"[^\w\-_\.]")

router = APIRouter(
    prefix="/admin",
    tags=["Admin Documents"],
)


# ---------------------------------------------------------------------------
# Fonctions utilitaires privées
# ---------------------------------------------------------------------------

def _sanitize_filename(filename: str) -> str:
    name = filename.strip().replace(" ", "_")
    return _SAFE_FILENAME_PATTERN.sub("_", name)


# Routes

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Uploader et indexer un document",
    description=(
        "Upload un fichier PDF ou DOCX, le sauvegarde sur disque "
        "et l'indexe dans ChromaDB via le pipeline RAG. "
        "Le document devient immédiatement disponible pour les questions utilisateurs."
    ),
)
async def upload_document(
    file: UploadFile = File(..., description="Fichier PDF ou DOCX à indexer"),
    admin: str = Depends(require_admin_user),
) -> DocumentUploadResponse:
    """
    Pipeline complet d'upload + indexation d'un document.

    Flux :
      1. Lecture du contenu binaire depuis la requête multipart
      2. Validation (extension, taille)
      3. Nettoyage du nom de fichier
      4. Sauvegarde sur disque dans data/uploaded_docs/
      5. Indexation dans ChromaDB (loader → chunker → embedder)
      6. Retour du nombre de chunks créés

    Pourquoi 'async' ici ?
      UploadFile.read() est une coroutine asynchrone — FastAPI gère
      les uploads de fichiers de manière non-bloquante.
      Les autres routes peuvent rester synchrones car elles ne font
      pas d'I/O réseau long.
    """
    logger.info(f"Admin '{admin}' uploade le fichier : {file.filename}")

    # Lecture du contenu binaire
    content = await file.read()

    # Validation extension + taille
    error = validate_file(file.filename, len(content))
    if error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error,
        )

    # Nettoyage du nom de fichier
    safe_filename = _sanitize_filename(file.filename)

    try:
        # Sauvegarde sur disque
        file_path = save_file_to_disk(safe_filename, content)

        # Indexation dans ChromaDB
        chunks_count = index_document(file_path)

    except ValueError as e:
        # Erreur métier (document vide, illisible...)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Erreur d'indexation pour '{safe_filename}' : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'indexation : {str(e)}",
        )

    return DocumentUploadResponse(
        filename=safe_filename,
        chunks_indexed=chunks_count,
        message=f"'{safe_filename}' indexé avec succès ({chunks_count} chunks).",
    )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Lister les documents indexés",
    description=(
        "Retourne la liste de tous les documents distincts indexés dans ChromaDB, "
        "avec leur nombre de chunks et leur taille sur disque."
    ),
)
def get_documents(
    admin: str = Depends(require_admin_user),
) -> DocumentListResponse:
    logger.info(f"Admin '{admin}' consulte la liste des documents")

    try:
        raw_docs = list_indexed_documents()
    except Exception as e:
        logger.error(f"Erreur lors du listing des documents : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des documents : {str(e)}",
        )

    documents = [DocumentInfo(**doc) for doc in raw_docs]

    return DocumentListResponse(
        documents=documents,
        total_documents=len(documents),
    )


@router.delete(
    "/documents/{filename}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Supprimer un document",
    description=(
        "Supprime tous les chunks d'un document de ChromaDB "
        "et supprime le fichier du disque. "
        "Cette action est irréversible."
    ),
)
def delete_document(
    filename: str,
    admin: str = Depends(require_admin_user),
) -> DocumentDeleteResponse:
    """
    Suppression complète d'un document : ChromaDB + disque.

    Ordre des opérations intentionnel :
      1. D'abord supprimer de ChromaDB (opération principale)
      2. Ensuite supprimer le fichier disque (secondaire)

    Si la suppression ChromaDB échoue → on s'arrête, le fichier reste.
    Si la suppression disque échoue → on log un warning mais on retourne
    succès (les chunks sont déjà supprimés, l'essentiel est fait).

    Args:
        filename : nom exact du fichier (doit correspondre au champ "source" ChromaDB)
    """
    logger.info(f"Admin '{admin}' supprime le document : {filename}")

    # Nettoyage du nom pour éviter les path traversal
    safe_filename = _sanitize_filename(filename)

    try:
        # Étape 1 — Suppression des chunks dans ChromaDB
        chunks_deleted = delete_document_from_index(safe_filename)

        if chunks_deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{safe_filename}' introuvable dans l'index.",
            )

        # Étape 2 — Suppression du fichier disque
        file_deleted = delete_file_from_disk(safe_filename)

        if not file_deleted:
            logger.warning(
                f"Chunks supprimés de ChromaDB mais fichier disque introuvable : {safe_filename}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de '{safe_filename}' : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression : {str(e)}",
            
        )

    return DocumentDeleteResponse(
        filename=safe_filename,
        chunks_deleted=chunks_deleted,
        message=f"'{safe_filename}' supprimé avec succès ({chunks_deleted} chunks retirés de l'index).",
    )

@router.get(
    "/history",
    response_model=HistoryPageResponse,
    status_code=status.HTTP_200_OK,
    summary="Historique global des conversations",
)
def get_history(
    skip:  int     = 0,
    limit: int     = 50,
    admin: User    = Depends(require_admin_user),
    db:    Session = Depends(get_db),
) -> HistoryPageResponse:
    conversations = get_all_conversations(db, skip=skip, limit=limit)
    total         = get_conversations_count(db)

    records = [
        ConversationRecord(
            id=c.id,
            username=c.user.username,
            question=c.question,
            answer=c.answer,
            module=c.module,
            source=c.source,
            created_at=c.created_at.isoformat(),
        )
        for c in conversations
    ]

    return HistoryPageResponse(
        conversations=records,
        total=total,
        skip=skip,
        limit=limit,
    )