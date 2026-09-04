"""
embedder.py
===========
Génération des embeddings et stockage vectoriel dans ChromaDB.

Deux collections partagent le même client et le même modèle d'embedding :
  - COLLECTION_NAME      : documentation officielle BeHave (permanente)
  - TEMP_COLLECTION_NAME : fichiers uploadés par les utilisateurs, isolés
                           par chat_id (mini-RAG, données temporaires)
"""

import uuid
import logging
from pathlib import Path
from dotenv import load_dotenv

from document_loader import Document

logger = logging.getLogger(__name__)
load_dotenv(Path(__file__).parent.parent / ".env")

COLLECTION_NAME      = "behave_docs"
TEMP_COLLECTION_NAME = "chat_temp_files"
EMBEDDING_MODEL      = "all-MiniLM-L6-v2"


class BeHaveVectorStore:
    """Encapsule ChromaDB + SentenceTransformer pour le pipeline RAG BeHave."""

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        self.persist_directory = persist_directory
        self.collection_name   = collection_name
        self._client            = None
        self._collection        = None
        self._temp_collection   = None
        self._embedding_model   = None
        self._doc_count: int    = 0

        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        self._init_chromadb()
        self._init_embedding_model()

    def _init_chromadb(self) -> None:
        """Initialise le client ChromaDB persistant et les deux collections."""
        import chromadb

        self._client = chromadb.PersistentClient(path=self.persist_directory)

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._temp_collection = self._client.get_or_create_collection(
            name=TEMP_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        self._doc_count = self._collection.count()
        logger.info(
            "ChromaDB prêt — collection '%s' (%d documents), collection temp '%s' (%d chunks)",
            self.collection_name, self._doc_count,
            TEMP_COLLECTION_NAME, self._temp_collection.count(),
        )

    def _init_embedding_model(self) -> None:
        """Charge le modèle SentenceTransformer, partagé entre les deux collections."""
        from sentence_transformers import SentenceTransformer

        logger.info("Chargement du modèle : %s ...", EMBEDDING_MODEL)
        self._embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        dim = self._embedding_model.get_embedding_dimension()
        logger.info("Modèle chargé — %d dimensions", dim)

    def _embed_texts(
        self,
        texts: list[str],
        show_progress: bool = False,
    ) -> list[list[float]]:
        """Encode une liste de textes en vecteurs normalisés."""
        embeddings = self._embedding_model.encode(
            texts,
            show_progress_bar=show_progress,
            batch_size=32,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def add_documents(
        self,
        documents: list[Document],
        batch_size: int = 100,
    ) -> int:
        """
        Encode et indexe une liste de Documents dans la collection permanente
        (upsert — idempotent).

        Returns:
            Nombre total de chunks indexés lors de cet appel.
        """
        if not documents:
            logger.warning("add_documents appelé avec une liste vide.")
            return 0

        total_batches = (len(documents) + batch_size - 1) // batch_size
        total_added   = 0

        logger.info(
            "Indexation de %d chunks en %d batch(es)...",
            len(documents), total_batches,
        )

        ids:       list[str]  = []
        texts:     list[str]  = []
        metadatas: list[dict] = []

        for batch_num in range(total_batches):
            start = batch_num * batch_size
            end   = min(start + batch_size, len(documents))
            batch = documents[start:end]

            logger.info(
                "  Batch %d/%d (chunks %d–%d)...",
                batch_num + 1, total_batches, start, end - 1,
            )

            ids.clear()
            texts.clear()
            metadatas.clear()

            for doc in batch:
                chunk_id = doc.metadata.get(
                    "chunk_id",
                    f"chunk_{total_added + len(ids):06d}",
                )
                ids.append(chunk_id)
                texts.append(doc.page_content)
                metadatas.append(_clean_metadata(doc.metadata))

            embeddings = self._embed_texts(texts, show_progress=True)
            self._collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            total_added += len(batch)
            logger.info("    %d/%d chunks indexés", total_added, len(documents))

        self._doc_count = self._collection.count()
        logger.info(
            "Indexation terminée — %d ajoutés, %d total dans la collection.",
            total_added, self._doc_count,
        )
        return total_added

    def search(self, query: str, k: int = 3) -> list[Document]:
        """
        Recherche les k chunks les plus similaires à la requête dans la
        collection permanente (documentation BeHave).
        Retourne [] si la collection est vide.
        """
        if self._doc_count == 0:
            logger.warning("search() appelé sur une collection vide.")
            return []

        effective_k     = min(k, self._doc_count)
        query_embedding = self._embed_texts([query], show_progress=False)[0]

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=effective_k,
            include=["documents", "metadatas", "distances"],
        )

        return _build_documents_from_query(results)

    def add_temp_chunks(self, documents: list[Document], chat_id: str) -> int:
        """
        Indexe des chunks de fichiers uploadés dans la collection temporaire,
        marqués avec chat_id pour isolation par conversation.

        Returns:
            Nombre de chunks indexés.
        """
        if not documents:
            return 0

        ids:       list[str]  = []
        texts:     list[str]  = []
        metadatas: list[dict] = []

        for doc in documents:
            ids.append(f"temp_{chat_id}_{uuid.uuid4().hex[:8]}")
            texts.append(doc.page_content)
            metadatas.append(_clean_metadata({**doc.metadata, "chat_id": str(chat_id)}))

        embeddings = self._embed_texts(texts, show_progress=False)
        self._temp_collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(
            "add_temp_chunks : %d chunks indexés pour chat_id=%s",
            len(documents), chat_id,
        )
        return len(documents)

    def delete_temp_chunks(self, chat_id: str) -> int:
        """
        Supprime tous les chunks de fichiers associés à un chat_id.

        Returns:
            Nombre de chunks supprimés.
        """
        results = self._temp_collection.get(where={"chat_id": str(chat_id)})
        chunk_ids = results.get("ids", [])

        if not chunk_ids:
            return 0

        self._temp_collection.delete(ids=chunk_ids)
        logger.info(
            "delete_temp_chunks : %d chunks supprimés pour chat_id=%s",
            len(chunk_ids), chat_id,
        )
        return len(chunk_ids)

    def search_temp(self, query: str, chat_id: str, k: int = 3) -> list[Document]:
        """
        Recherche les k chunks les plus pertinents parmi les fichiers uploadés
        pour un chat_id donné. Retourne [] si aucun fichier indexé pour ce chat.
        """
        temp_count = self._temp_collection.count()
        if temp_count == 0:
            return []

        query_embedding = self._embed_texts([query], show_progress=False)[0]

        results = self._temp_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, temp_count),
            where={"chat_id": str(chat_id)},
            include=["documents", "metadatas", "distances"],
        )

        return _build_documents_from_query(results)

    def get_collection_info(self) -> dict:
        """Résumé de la collection — utilise le cache _doc_count."""
        return {
            "collection_name":   self.collection_name,
            "document_count":    self._doc_count,
            "persist_directory": self.persist_directory,
            "embedding_model":   EMBEDDING_MODEL,
        }

    def clear_collection(self, confirm: bool = False) -> None:
        """
        Vide la collection permanente ChromaDB.

        Raises:
            RuntimeError : si confirm=False (protection contre suppression accidentelle).
        """
        if not confirm:
            raise RuntimeError(
                "clear_collection() nécessite confirm=True. "
                "Appelez clear_collection(confirm=True) explicitement."
            )

        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._doc_count = 0
        logger.info("Collection '%s' vidée.", self.collection_name)

    def delete_by_source(self, source: str) -> int:
        """
        Supprime tous les chunks d'un document via son champ 'source'.

        Returns:
            int : nombre de chunks supprimés
        """
        results   = self._collection.get(where={"source": source})
        chunk_ids = results.get("ids", [])

        if not chunk_ids:
            return 0

        self._collection.delete(ids=chunk_ids)
        self._doc_count = self._collection.count()
        logger.info(
            "delete_by_source : %d chunks supprimés pour '%s'",
            len(chunk_ids), source,
        )
        return len(chunk_ids)

    def get_all_metadatas(self) -> list[dict]:
        """
        Retourne toutes les métadonnées de la collection sans les vecteurs.

        Returns:
            list[dict] : métadonnées de chaque chunk indexé
        """
        results = self._collection.get(include=["metadatas"])
        return results.get("metadatas", [])


def _build_documents_from_query(results: dict) -> list[Document]:
    """Reconstruit une liste de Document à partir d'un résultat ChromaDB .query()."""
    if not results["documents"] or not results["documents"][0]:
        return []

    retrieved: list[Document] = []
    for text, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        similarity = round(1.0 - distance / 2.0, 4)
        retrieved.append(Document(
            page_content=text,
            metadata={**metadata, "similarity_score": similarity},
        ))
    return retrieved


def _clean_metadata(metadata: dict) -> dict:
    """ChromaDB n'accepte que str, int, float, bool — convertit le reste."""
    clean: dict = {}
    for key, value in metadata.items():
        if value is None:
            clean[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            clean[key] = value
        else:
            clean[key] = str(value)
    return clean


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    logger.info("embedder.py chargé — BeHaveVectorStore disponible")
    logger.info("Modèle : %s | Collection : %s", EMBEDDING_MODEL, COLLECTION_NAME)