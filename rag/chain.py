"""
chain.py
========
Orchestrateur principal du pipeline RAG BeHave.

Flux par question :
    question (+ chat_id optionnel)
        ↓ retriever.retrieve_temp_files(chat_id)  → chunks fichiers uploadés (si chat_id fourni)
        ↓ si chunks fichiers pertinents trouvés    → mode "fichier" (has_file=True)
        ↓ sinon : retriever.retrieve()             → chunks doc BeHave (mode standard)
        ↓ _detect_module_from_chunks()             → module détecté par meilleur score (mode standard uniquement)
        ↓ build_prompt()                           → (system prompt, user_message + contexte chunks)
        ↓ Groq API (GPT OSS 20B)                   → réponse brute
        ↓ parse_response()                         → {"content", "module", "source"}
        ↓ override module                          → module depuis ChromaDB (mode standard uniquement)

Les fichiers uploadés par l'utilisateur sont indexés en amont (main.py, via
BeHaveVectorStore.add_temp_chunks) dans une collection ChromaDB isolée par
chat_id. Ils sont ensuite récupérés par retrieval comme la documentation
BeHave — plus de branche "texte brut injecté dans le prompt".

Performance :
    - Le retriever (ChromaDB + embedding) est partagé entre toutes les sessions
      via injection dans __init__ — chargé une seule fois au démarrage.
    - Seul l'historique RAG (_history) est isolé par session/chat.
"""

import os
import logging
from dotenv import load_dotenv
from pathlib import Path

from groq import Groq

from retriever import BeHaveRetriever
from prompt_builder import build_prompt, parse_response

load_dotenv(Path(__file__).parent.parent / ".env")
logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────

_GROQ_MODEL_TEXT:     str   = os.getenv("GROQ_MODEL_TEXT",          "openai/gpt-oss-20b")
_MAX_TOKENS:          int   = int(os.getenv("GROQ_MAX_TOKENS",       "1024"))
_MAX_TOKENS_FILE:     int   = int(os.getenv("GROQ_MAX_TOKENS_FILE",  "2048"))
_TEMPERATURE:         float = float(os.getenv("GROQ_TEMPERATURE",    "0.2"))
_MAX_HISTORY_TURNS:   int   = int(os.getenv("RAG_MAX_HISTORY_TURNS", "10"))
_DEFAULT_K:           int   = int(os.getenv("RAG_K",                 "4"))
_MIN_RELEVANCE_SCORE: float = float(os.getenv("RAG_MIN_RELEVANCE_SCORE", "0.55"))

_FALLBACK_RESPONSE: dict = {
    "content": (
        "Je suis temporairement indisponible. "
        "Veuillez réessayer dans quelques instants."
    ),
    "module": None,
    "source": None,
}


# ─── Fonctions privées ────────────────────────────────────────────────────────

def _detect_module_from_chunks(chunks: list) -> str | None:
    """
    Déduit le module BeHave depuis le chunk avec le meilleur score de similarité.
    Ce chunk est le plus pertinent — son module est le plus fiable.
    """
    if not chunks:
        return None

    best_chunk = max(
        chunks,
        key=lambda c: c.metadata.get("similarity_score", 0.0),
    )

    module = best_chunk.metadata.get("module", "").strip()
    if not module or module == "BeHave (module inconnu)":
        return None

    logger.debug(
        "_detect_module_from_chunks : best_score=%.4f → module='%s'",
        best_chunk.metadata.get("similarity_score", 0.0), module,
    )
    return module


def _best_score(chunks: list) -> float:
    """Retourne le meilleur score de similarité d'une liste de chunks, 0.0 si vide."""
    if not chunks:
        return 0.0
    return max(c.metadata.get("similarity_score", 0.0) for c in chunks)


# ─── Classe principale ────────────────────────────────────────────────────────

class BeHaveRAGChain:
    """
    Chaîne RAG complète : retrieval → prompt → LLM → parsing.

    Le retriever (ChromaDB + embedding) est injecté depuis l'extérieur et partagé
    entre toutes les sessions — chargé une seule fois au démarrage du serveur.
    Seul l'historique (_history) est propre à chaque instance (session/chat).

    Usage :
        # Au démarrage — une seule fois
        shared_retriever = BeHaveRetriever()
        chain = BeHaveRAGChain(retriever=shared_retriever)

        # Par session/chat — instanciation légère
        session_chain = BeHaveRAGChain(retriever=shared_retriever)
    """

    def __init__(
        self,
        k: int = _DEFAULT_K,
        retriever: BeHaveRetriever | None = None,
    ) -> None:
        self.k = k

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY manquante. "
                "Ajoutez-la dans le fichier .env : GROQ_API_KEY=gsk_..."
            )

        self.client    = Groq(api_key=api_key)
        self.retriever = retriever if retriever is not None else BeHaveRetriever()
        self._history: list[dict] = []

        logger.info(
            "BeHaveRAGChain prête — modèle=%s | k=%d | min_score=%.2f | retriever=%s",
            _GROQ_MODEL_TEXT, self.k, _MIN_RELEVANCE_SCORE,
            "partagé" if retriever is not None else "nouveau",
        )

    def ask(
        self,
        question: str,
        chat_id: str | None = None,
    ) -> dict[str, str | None]:
        """
        Pose une question et retourne une réponse structurée.

        Si chat_id est fourni, cherche à la fois dans les fichiers uploadés pour
        ce chat (mini-RAG) et dans la documentation BeHave. Le mode retenu est
        celui dont le meilleur score de similarité est le plus élevé — une
        question hors sujet par rapport au fichier retombe donc naturellement
        sur le RAG BeHave standard, même après un upload dans le même chat.

        Returns:
            {"content": str, "module": str|None, "source": str|None}

        Ne propage jamais d'exception : toute erreur retourne _FALLBACK_RESPONSE.
        """
        if not question or not question.strip():
            logger.warning("ask() : question vide.")
            return {"content": "", "module": None, "source": None}

        history_len_before = len(self._history)

        try:
            file_chunks: list = []
            if chat_id:
                file_chunks = self.retriever.retrieve_temp_files(
                    question, chat_id=chat_id, k=self.k,
                )
                file_chunks = [
                    c for c in file_chunks
                    if c.metadata.get("similarity_score", 0.0) >= _MIN_RELEVANCE_SCORE
                ]

            behave_chunks = self.retriever.retrieve(question, k=self.k)
            behave_chunks = [
                c for c in behave_chunks
                if c.metadata.get("similarity_score", 0.0) >= _MIN_RELEVANCE_SCORE
            ]

            file_best_score   = _best_score(file_chunks)
            behave_best_score = _best_score(behave_chunks)
            has_file = bool(file_chunks) and file_best_score >= behave_best_score

            if has_file:
                relevant_chunks  = file_chunks
                retrieved_module = None
            else:
                relevant_chunks  = behave_chunks
                retrieved_module = _detect_module_from_chunks(relevant_chunks)

            system_prompt, user_message = build_prompt(
                question,
                relevant_chunks,
                has_file=has_file,
            )

            self._history.append({"role": "user", "content": question})

            max_tokens       = _MAX_TOKENS_FILE if has_file else _MAX_TOKENS
            history_to_send  = self._get_bounded_history()[:-1]

            response = self.client.chat.completions.create(
                model=_GROQ_MODEL_TEXT,
                max_tokens=max_tokens,
                temperature=_TEMPERATURE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *history_to_send,
                    {"role": "user",   "content": user_message},
                ],
            )

            raw_answer: str | None = response.choices[0].message.content

            if not raw_answer:
                logger.warning(
                    "Groq : réponse vide (finish_reason=%s).",
                    response.choices[0].finish_reason,
                )
                self._history[:] = self._history[:history_len_before]
                return _FALLBACK_RESPONSE

            parsed = parse_response(raw_answer)

            if not has_file and retrieved_module is not None:
                parsed["module"] = retrieved_module

            self._history.append({"role": "assistant", "content": raw_answer})

            logger.info(
                "ask() OK — has_file=%s | module=%s | %d chars",
                has_file, parsed.get("module"), len(parsed["content"]),
            )
            return parsed

        except Exception as exc:
            self._history[:] = self._history[:history_len_before]
            logger.exception("Erreur dans ask() pour %r : %s", question, exc)
            return _FALLBACK_RESPONSE

    def reset_history(self) -> bool:
        """Réinitialise l'historique de cette session."""
        self._history.clear()
        logger.info("Historique réinitialisé.")
        return True

    @property
    def history(self) -> list[dict]:
        """Copie défensive de l'historique complet."""
        return list(self._history)

    @property
    def history_turns(self) -> int:
        """Nombre de tours de conversation (paires user/assistant)."""
        return len(self._history) // 2

    def _get_bounded_history(self) -> list[dict]:
        """Retourne une COPIE de l'historique borné à _MAX_HISTORY_TURNS."""
        max_messages = _MAX_HISTORY_TURNS * 2
        if len(self._history) <= max_messages:
            return list(self._history)

        truncated = self._history[-max_messages:]
        logger.debug(
            "Historique tronqué : %d → %d messages.",
            len(self._history), len(truncated),
        )
        return list(truncated)