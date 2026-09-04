"""
retriever.py
============
Recherche des chunks pertinents dans ChromaDB pour une question donnée.

retrieve()            : documentation BeHave (collection permanente)
retrieve_temp_files()  : fichiers uploadés par l'utilisateur (collection
                         temporaire, filtrée par chat_id)
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

_env_loaded = load_dotenv(Path(__file__).parent.parent / ".env")
if not _env_loaded:
    logging.getLogger(__name__).debug(
        "Fichier .env non trouvé — utilisation des valeurs par défaut."
    )

from embedder import BeHaveVectorStore

logger = logging.getLogger(__name__)


_DEFAULT_CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"
CHROMA_DB_DIR: Path = Path(
    os.getenv("CHROMA_DB_DIR", str(_DEFAULT_CHROMA_DIR))
)

DEFAULT_MIN_SCORE: float = float(os.getenv("RETRIEVER_MIN_SCORE", "0.0"))


class BeHaveRetriever:
    """
    Encapsule BeHaveVectorStore avec filtrage par score et logging structuré.
    retrieve() et retrieve_temp_files() retournent toujours une list, jamais None.
    """

    def __init__(self, min_score: float = DEFAULT_MIN_SCORE) -> None:
        self.min_score = min_score
        logger.info("Chargement base vectorielle : %s", CHROMA_DB_DIR)
        self.store = BeHaveVectorStore(persist_directory=str(CHROMA_DB_DIR))
        logger.info(
            "Retriever prêt — %d documents indexés",
            self.store.get_collection_info()["document_count"],
        )

    def retrieve(self, query: str, k: int = 3) -> list:
        """
        Recherche les k chunks les plus pertinents dans la documentation BeHave.

        Returns:
            Liste de Documents (peut être vide, jamais None).
        """
        if not query or not query.strip():
            logger.warning("retrieve() : question vide ignorée.")
            return []

        results = self.store.search(query, k=k)
        results = self._filter_by_score(results)

        if not results:
            logger.warning("Aucun chunk pertinent trouvé pour : %r", query)
        else:
            self._log_results(results)

        return results

    def retrieve_temp_files(self, query: str, chat_id: str, k: int = 3) -> list:
        """
        Recherche les k chunks les plus pertinents parmi les fichiers uploadés
        dans ce chat_id.

        Returns:
            Liste de Documents (peut être vide, jamais None).
        """
        if not query or not query.strip() or not chat_id:
            return []

        results = self.store.search_temp(query, chat_id=chat_id, k=k)
        results = self._filter_by_score(results)

        if results:
            self._log_results(results)

        return results

    def _filter_by_score(self, results: list) -> list:
        if self.min_score <= 0.0:
            return results

        before  = len(results)
        results = [
            doc for doc in results
            if doc.metadata.get("similarity_score", 0.0) >= self.min_score
        ]
        filtered = before - len(results)
        if filtered:
            logger.debug(
                "%d chunk(s) filtré(s) (score < %.2f)",
                filtered, self.min_score,
            )
        return results

    def _log_results(self, results: list) -> None:
        for i, doc in enumerate(results):
            score  = doc.metadata.get("similarity_score", None)
            module = doc.metadata.get("module", "?")

            if isinstance(score, (int, float)):
                logger.debug("  [%d] score=%.4f | %s", i + 1, score, module)
            else:
                logger.debug("  [%d] score=N/A | %s", i + 1, module)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    retriever = BeHaveRetriever()

    questions = [
        "Comment créer un client dans BeHave Master Data ?",
        "Quels modèles IA utilise BeHave Predictive ?",
        "Comment fonctionne la gouvernance des accès SAP ?",
    ]

    for question in questions:
        logger.info("Question : %s", question)
        chunks = retriever.retrieve(question, k=3)

        if not chunks:
            logger.info("  Aucun résultat.")
            continue

        for i, chunk in enumerate(chunks):
            score  = chunk.metadata.get("similarity_score", None)
            module = chunk.metadata.get("module", "?")
            score_str = f"{score:.4f}" if isinstance(score, (int, float)) else "N/A"
            logger.info("  [%d] score=%s | %s", i + 1, score_str, module)
            logger.info("       %s...", chunk.page_content[:120])