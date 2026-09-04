"""
prompt_builder.py
=================
Construction du prompt envoyé au LLM et parsing de sa réponse structurée.

Flux :
    chunks + question
        ↓ build_prompt()   → (system_prompt, user_message)
        ↓ LLM
        ↓ parse_response() → {"content", "module", "source"}

has_file=True signifie que les chunks proviennent des fichiers uploadés par
l'utilisateur (collection temporaire), pas de la documentation BeHave.
Dans les deux cas, le contexte est construit depuis des chunks récupérés
par le retriever — seul le prompt système et le formatage du contexte changent.

Note : le champ "module" retourné par parse_response() est toujours None.
Le module réel est détecté depuis les métadonnées ChromaDB dans chain.py
via _detect_module_from_chunks() — le LLM n'est plus responsable de cette tâche.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ─── Patterns compilés une seule fois au chargement du module ─────────────────

_RE_PARASITIC_TAGS: re.Pattern = re.compile(
    r"\[R[ée]PONSE\]"
    r"|\[Ton explication ici,\s*claire et structur[ée]e?\.\]",
    re.IGNORECASE,
)

_RE_SOURCE_TAG: re.Pattern = re.compile(r"\[source\]", re.IGNORECASE)

_NA_VALUES: frozenset = frozenset({"non applicable", "n/a", ""})

# ─── Prompts système ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT: str = """Tu es BeHave Assistant, un assistant IA spécialisé \
dans la suite logicielle BeHave de Siryos.
Tu réponds aux questions en te basant UNIQUEMENT sur la documentation \
officielle BeHave fournie.

RÈGLES :
- Réponds TOUJOURS dans la même langue que la question de l'utilisateur
- Pour les salutations simples (bonjour, bonsoir, etc.), réponds poliment sans mentionner la documentation
- Base-toi uniquement sur le contexte fourni
- Sois précis et concis
- Si tu ne trouves pas l'information dans la documentation fournie, dis-le clairement

QUESTION HORS SUJET : si la question ne concerne pas BeHave, réponds exactement :
[RÉPONSE]
Je suis BeHave Assistant et je suis conçu uniquement pour répondre aux questions \
sur la suite BeHave (Predictive, Access, Master Data, Analytics). \
Je ne peux pas vous aider sur ce sujet. \
N'hésitez pas à me poser une question sur BeHave !
[SOURCE]
Document: Non applicable

STRUCTURE OBLIGATOIRE POUR TOUTE RÉPONSE :
[RÉPONSE]
<ton explication claire et structurée>
[SOURCE]
Document: <nom exact du fichier source si l'information provient de la documentation, sinon Non applicable>

IMPORTANT :
- Ne mets JAMAIS de texte avant [RÉPONSE]
- Ne mets JAMAIS de texte après [SOURCE]
- Respecte TOUJOURS ce format sans exception
"""

_SYSTEM_PROMPT_WITH_FILE: str = """Tu es BeHave Assistant, un assistant IA spécialisé \
dans la suite logicielle BeHave de Siryos.

Un ou plusieurs fichiers externes ont été joints par l'utilisateur dans cette \
conversation. Des extraits pertinents de ces fichiers te sont fournis ci-dessous.
Tu dois répondre à la question en te basant sur le contenu de ces extraits.

RÈGLES :
- Réponds TOUJOURS dans la même langue que la question de l'utilisateur
- Base-toi principalement sur les extraits du fichier fournis
- Sois précis et concis
- Si l'information demandée n'est pas dans les extraits fournis, dis-le clairement

STRUCTURE OBLIGATOIRE POUR TOUTE RÉPONSE :
[RÉPONSE]
<ton explication claire et structurée basée sur le fichier joint>
[SOURCE]
Document: <nom exact du fichier si mentionné dans les extraits, sinon Non applicable>

IMPORTANT :
- Ne mets JAMAIS de texte avant [RÉPONSE]
- Ne mets JAMAIS de texte après [SOURCE]
- Respecte TOUJOURS ce format sans exception
"""


def get_system_prompt(has_file: bool = False) -> str:
    """
    Retourne le prompt système adapté au contexte.

    Args:
        has_file : True si des chunks de fichiers uploadés sont utilisés comme
                   contexte — utilise un prompt dédié qui autorise les questions
                   sur ce fichier et évite la réponse "hors sujet BeHave".
    """
    return _SYSTEM_PROMPT_WITH_FILE if has_file else _SYSTEM_PROMPT


def _build_context(chunks: list, has_file: bool) -> str:
    """Formate les chunks récupérés en un bloc de contexte pour le prompt."""
    if has_file:
        return "\n\n".join(
            f"[Extrait {i + 1} — {c.metadata.get('filename', 'fichier joint')}] :\n{c.page_content}"
            for i, c in enumerate(chunks)
        )

    return "\n\n".join(
        f"[Source {i + 1} — {c.metadata.get('module', 'BeHave')} "
        f"({c.metadata.get('source', 'doc')})] :\n{c.page_content}"
        for i, c in enumerate(chunks)
    )


def build_prompt(
    question: str,
    chunks: list,
    has_file: bool = False,
) -> tuple[str, str]:
    """
    Construit le prompt complet pour le LLM à partir des chunks récupérés.

    Args:
        question : question de l'utilisateur.
        chunks   : chunks récupérés par le retriever (fichier uploadé ou
                   documentation BeHave selon has_file).
        has_file : True si chunks provient de la collection temporaire
                   (fichiers uploadés) plutôt que de la documentation BeHave.

    Returns:
        Tuple (system_prompt, user_message).
    """
    if not chunks:
        logger.warning(
            "build_prompt : 0 chunk pour %r (has_file=%s) — le LLM répondra sans contexte.",
            question, has_file,
        )

    context = _build_context(chunks, has_file)
    label   = "Contenu du fichier joint" if has_file else "Documentation BeHave"

    user_message = (
        f"{label} :\n\n{context}\n\n"
        f"---\n"
        f"Question : {question}\n\n"
        f"Rappel : utilise OBLIGATOIREMENT le format "
        f"[RÉPONSE] ... [SOURCE] Document: ..."
    )

    return get_system_prompt(has_file), user_message


def parse_response(raw_answer: str | None) -> dict[str, str | None]:
    """
    Parse la réponse brute du LLM.

    Robuste contre : None, vide, [source] minuscule, [SOURCE] absent.

    Returns:
        {"content": str, "module": None, "source": str|None}

        "module" est toujours None ici — il est injecté en override
        depuis les métadonnées ChromaDB dans chain.py.
        "content" est toujours une str, jamais None.
    """
    if not raw_answer:
        logger.warning("parse_response : raw_answer vide ou None.")
        return {"content": "", "module": None, "source": None}

    normalized = _RE_SOURCE_TAG.sub("[SOURCE]", raw_answer)

    if "[SOURCE]" in normalized:
        content_part, source_part = normalized.split("[SOURCE]", 1)
        content = _clean_tags(content_part)
        source  = _parse_source_block(source_part)
    else:
        logger.warning("parse_response : balise [SOURCE] absente — retour texte brut.")
        content = _clean_tags(normalized)
        source  = None

    return {"content": content, "module": None, "source": source}


def _clean_tags(text: str) -> str:
    """Supprime les balises parasites en une seule passe regex."""
    return _RE_PARASITIC_TAGS.sub("", text).strip()


def _parse_source_block(block: str) -> str | None:
    """
    Extrait le nom du document depuis le bloc [SOURCE].

    Retourne None si la valeur est absente ou non applicable.
    Le module n'est plus extrait ici — il vient de ChromaDB (chain.py).
    """
    for line in block.splitlines():
        line = line.strip()
        if line.lower().startswith("document:"):
            val = line.split(":", 1)[1].strip()
            return None if val.lower() in _NA_VALUES else val

    return None