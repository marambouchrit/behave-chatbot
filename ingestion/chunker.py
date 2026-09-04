"""
chunker.py
==========
Découpage des documents BeHave en chunks pour l'indexation RAG.
"""

import re
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from document_loader import Document

logger = logging.getLogger(__name__)


CHUNK_SIZE_CHARS    = 1500
CHUNK_OVERLAP_CHARS = 200
MAX_CHUNKS_PER_DOC  = 5

_RE_INVALID_ID_CHARS        = re.compile(r"[^\w\-.]")
_RE_CONSECUTIVE_UNDERSCORES = re.compile(r"_+")


def _sanitize_chunk_id(raw_id: str) -> str:
    """
    Nettoie un identifiant pour ChromaDB.
    ChromaDB n'accepte que [a-zA-Z0-9_-.].
    """
    sanitized = _RE_INVALID_ID_CHARS.sub("_", raw_id)
    sanitized = _RE_CONSECUTIVE_UNDERSCORES.sub("_", sanitized)
    return sanitized.strip("_")


def chunk_document(
    document: Document,
    chunk_size: int = CHUNK_SIZE_CHARS,
    chunk_overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[Document]:
    """
    Découpe un Document en chunks.

    Raises:
        ValueError : si chunk_overlap >= chunk_size.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) doit être < chunk_size ({chunk_size})."
        )

    if not document.page_content.strip():
        logger.warning(
            "Document vide ignoré lors du chunking : %s",
            document.metadata.get("source", "?"),
        )
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
        is_separator_regex=False,
    )

    raw_chunks: list[str] = splitter.split_text(document.page_content)
    source: str           = document.metadata.get("source", "doc")
    total: int            = len(raw_chunks)
    chunks: list[Document] = []

    for idx, chunk_text in enumerate(raw_chunks):
        chunk_text = chunk_text.strip()
        if not chunk_text:
            continue

        chunk_id = _sanitize_chunk_id(f"{source}__chunk_{idx:04d}")
        module   = document.metadata.get("module", "BeHave")

        chunks.append(Document(
            page_content=f"[{module}]\n{chunk_text}",
            metadata={
                **document.metadata,
                "chunk_index": idx,
                "chunk_total": total,
                "chunk_id":    chunk_id,
            },
        ))

    if len(chunks) > MAX_CHUNKS_PER_DOC:
        logger.warning(
            "%s tronqué : %d → %d chunks (MAX_CHUNKS_PER_DOC=%d)",
            source, len(chunks), MAX_CHUNKS_PER_DOC, MAX_CHUNKS_PER_DOC,
        )
        chunks = chunks[:MAX_CHUNKS_PER_DOC]

    logger.debug(
        "%s → %d chunks (moy. %d chars/chunk)",
        source,
        len(chunks),
        (len(document.page_content) // len(chunks)) if chunks else 0,
    )
    return chunks


def chunk_all_documents(
    documents: list[Document],
    chunk_size: int = CHUNK_SIZE_CHARS,
    chunk_overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[Document]:
    """Découpe une liste de Documents en chunks — tout via logger."""
    all_chunks: list[Document] = []

    for doc in documents:
        doc_chunks = chunk_document(doc, chunk_size, chunk_overlap)
        all_chunks.extend(doc_chunks)

        n_chunks  = len(doc_chunks)
        avg_chars = (len(doc.page_content) // n_chunks) if n_chunks else 0
        logger.info(
            "%s → %d chunks (~%d chars/chunk)",
            doc.metadata.get("source", "?"), n_chunks, avg_chars,
        )

    return all_chunks


def print_chunk_stats(chunks: list[Document]) -> None:
    """Affiche des statistiques descriptives sur les chunks produits."""
    chunks = list(chunks)

    if not chunks:
        logger.info("Aucun chunk à analyser.")
        return

    sizes = [len(c.page_content) for c in chunks]
    total = len(sizes)
    avg   = sum(sizes) / total

    by_module: dict[str, int] = {}
    for chunk in chunks:
        module = chunk.metadata.get("module", "Inconnu")
        by_module[module] = by_module.get(module, 0) + 1

    logger.info("Statistiques des chunks :")
    logger.info("  Total    : %d", total)
    logger.info("  Moyenne  : %.0f chars", avg)
    logger.info("  Min/Max  : %d / %d chars", min(sizes), max(sizes))
    logger.info("  Par module BeHave :")
    for module, count in sorted(by_module.items()):
        bar = "█" * max(1, count * 20 // total)
        logger.info("    • %-35s %3d chunks  %s", module, count, bar)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s  %(message)s")

    sample = ("BeHave Predictive est une plateforme IA.\n"
              "Elle supporte LSTM, TCN et TSMixer.\n\n") * 15

    test_doc = Document(
        page_content=sample,
        metadata={"source": "test.docx", "module": "BeHave Predictive", "file_type": "docx"},
    )

    chunks = chunk_document(test_doc)
    logger.info("Document : %d chars → %d chunks", len(test_doc.page_content), len(chunks))

    try:
        chunk_document(test_doc, chunk_size=100, chunk_overlap=200)
    except ValueError as e:
        logger.info("Validation OK → %s", e)

    ugly = "Mon fichier (v2).docx__chunk_0000"
    logger.info("Sanitize : %r → %r", ugly, _sanitize_chunk_id(ugly))

    print_chunk_stats(chunks)