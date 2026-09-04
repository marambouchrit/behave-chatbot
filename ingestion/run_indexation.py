"""
run_indexation.py
=================
Script d'indexation offline .

Orchestre les 3 étapes :
  1. CHARGEMENT  : lecture des DOCX/PDF depuis data/documents/
  2. CHUNKING    : découpage en morceaux de ~375 tokens
  3. EMBEDDING   : vecteurs + stockage persistant dans ChromaDB

À exécuter UNE SEULE FOIS (ou à chaque mise à jour des documents).
"""

import sys
import time
import logging
import argparse
from pathlib import Path

# __file__ = ingestion/run_indexation.py
# .parent  = ingestion/
# .parent  = chatbot_behave/   ← PROJECT_ROOT

PROJECT_ROOT   = Path(__file__).parent.parent
INGESTION_DIR  = Path(__file__).parent


if str(INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(INGESTION_DIR))

from document_loader import load_all_documents
from chunker import chunk_all_documents, print_chunk_stats
from embedder import BeHaveVectorStore


DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"
CHROMA_DB_DIR = PROJECT_ROOT / "data" / "chroma_db"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_indexation")


def run_indexation(reset: bool = False) -> BeHaveVectorStore:
    """
    Exécute le pipeline complet d'indexation.

    """
    start_time = time.perf_counter()  

    _print_header()
    logger.info("Démarrage du pipeline d'indexation (reset=%s)", reset)

    
    if not DOCUMENTS_DIR.exists():
        logger.error("Répertoire documents introuvable : %s", DOCUMENTS_DIR)
        print(f"\n  ✗ Répertoire introuvable : {DOCUMENTS_DIR}")
        print("    Créez ce dossier et placez-y vos fichiers PDF/DOCX.")
        sys.exit(1)

    print(f"  Documents source : {DOCUMENTS_DIR}")
    print(f"  Base vectorielle : {CHROMA_DB_DIR}\n")

    _print_step(1, "Chargement des documents")

    documents = load_all_documents(str(DOCUMENTS_DIR))

    if not documents:
        logger.error("Aucun document chargé depuis %s", DOCUMENTS_DIR)
        print("\n  ✗ Aucun document chargé.")
        print(f"    Vérifiez que des fichiers PDF/DOCX sont présents dans :\n    {DOCUMENTS_DIR}")
        sys.exit(1)

    print(f"\n  ✓ {len(documents)} document(s) chargé(s)")

   
    _print_step(2, "Découpage en chunks")

    chunks = chunk_all_documents(documents)

    if not chunks:
        logger.error("Aucun chunk produit — vérifiez le contenu des documents.")
        print("\n  ✗ Aucun chunk produit.")
        sys.exit(1)

    print_chunk_stats(chunks)

    
    _print_step(3, "Génération des embeddings et stockage ChromaDB")

    store = BeHaveVectorStore(persist_directory=str(CHROMA_DB_DIR))

    if reset:
        print("  Mode RESET : vidage de la collection...")
        store.clear_collection(confirm=True)  

    nb_indexed = store.add_documents(chunks)

    elapsed = time.perf_counter() - start_time
    _print_summary(len(documents), len(chunks), nb_indexed, elapsed)

    
    _run_smoke_test(store)

    return store


def _run_smoke_test(store: BeHaveVectorStore) -> None:
    """
    Vérifie que la base indexée répond correctement à une requête simple.
    Affiche un warning si les résultats sont vides ou ont un score trop faible.
    """
    TEST_QUERY     = "What is BeHave?"
    MIN_SCORE      = 0.3   
    EXPECTED_K     = 3

    print("\n  Vérification — Test de recherche :")
    print(f"  Requête : {TEST_QUERY!r}\n")

    results = store.search(TEST_QUERY, k=EXPECTED_K)

    if not results:
        logger.warning("Test de fumée : aucun résultat retourné.")
        print("  ⚠ Aucun résultat — base peut-être vide ?")
        return

    all_ok = True
    for i, doc in enumerate(results):
        score  = doc.metadata.get("similarity_score", 0)
        module = doc.metadata.get("module", "?")
        source = doc.metadata.get("source", "?")
        status = "✓" if score >= MIN_SCORE else "⚠"

        if score < MIN_SCORE:
            all_ok = False

        preview = doc.page_content[:100].replace("\n", " ")
        print(f"  [{i + 1}] {status} score={score:.4f} | {module} ({source})")
        print(f"      {preview}...")

    if all_ok:
        print("\n  ✓ Test de fumée réussi — pipeline opérationnel !")
        logger.info("Test de fumée réussi (%d résultats, score min %.4f)",
                    len(results), min(d.metadata.get("similarity_score", 0) for d in results))
    else:
        print(f"\n  ⚠ Certains scores sont inférieurs au seuil ({MIN_SCORE}).")
        print("    Vérifiez la qualité des documents ou augmentez CHUNK_SIZE.")
        logger.warning("Test de fumée : scores faibles détectés.")




def _print_header() -> None:
    print("=" * 65)
    print("  BeHave AI Chatbot — Pipeline d'Indexation")
    print("=" * 65)

def _print_step(n: int, label: str) -> None:
    print(f"\n{'─' * 65}")
    print(f"  ÉTAPE {n}/3 — {label}")
    print(f"{'─' * 65}")

def _print_summary(
    n_docs: int,
    n_chunks: int,
    n_indexed: int,
    elapsed: float,
) -> None:
    print(f"\n{'=' * 65}")
    print("  INDEXATION TERMINÉE")
    print(f"{'=' * 65}")
    print(f"    Documents traités  : {n_docs}")
    print(f"    Chunks produits    : {n_chunks}")
    print(f"    Chunks indexés     : {n_indexed}")
    print(f"    Durée totale       : {elapsed:.1f}s")



def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pipeline d'indexation BeHave AI Chatbot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples :\n"
            "  python ingestion/run_indexation.py\n"
            "  python ingestion/run_indexation.py --reset\n"
        ),
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Vider la base ChromaDB avant l'indexation (ré-indexation complète).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        run_indexation(reset=args.reset)
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n  Indexation interrompue par l'utilisateur.")
        logger.info("Indexation interrompue (KeyboardInterrupt).")
        sys.exit(1)