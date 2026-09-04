import { FiDatabase, FiFileText, FiFile } from "react-icons/fi";
import { getUser } from "../services/authApi";
// ─── Helpers ──────────────────────────────────────────────────────────────────

const _isImage = (attachment) => attachment.type.startsWith("image/");

// ─── Sous-composant : affichage des fichiers joints ───────────────────────────

const _Attachments = ({ attachments }) => {
  if (!attachments?.length) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-2">
      {attachments.map((attachment, index) =>
        _isImage(attachment) ? (
          // Image → miniature cliquable
          <a
            key={index}
            href={attachment.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Voir l'image ${attachment.name}`}
          >
            <img
              src={attachment.url}
              alt={attachment.name}
              className="max-w-[200px] max-h-[150px] rounded-lg object-cover
                         border border-white/20 hover:opacity-90
                         transition-opacity duration-150"
            />
          </a>
        ) : (
          // PDF / DOCX → pill avec icône
          <div
            key={index}
            className="flex items-center gap-1.5 bg-white/20 rounded-lg px-2 py-1"
          >
            <FiFile size={13} className="flex-shrink-0" aria-hidden="true" />
            <span className="text-xs truncate max-w-[140px]">
              {attachment.name}
            </span>
          </div>
        ),
      )}
    </div>
  );
};

// ─── Composant principal ──────────────────────────────────────────────────────

/**
 * MessageBubble
 *
 * Affiche un message utilisateur ou assistant.
 * Pour les messages utilisateur, affiche les fichiers joints
 * (images en miniature, PDF/DOCX en pill) au-dessus du texte.
 *
 * @param {object}   message
 * @param {string}   message.role         "user" | "assistant"
 * @param {string}   message.content      Texte du message
 * @param {object[]} message.attachments  Fichiers joints (optionnel, messages user uniquement)
 *                                        [{name, type, url}]
 * @param {string}   message.module       Module BeHave source (optionnel, messages assistant)
 * @param {string}   message.source       Fichier source RAG (optionnel, messages assistant)
 */
function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex items-end gap-2 mb-4 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center
                       flex-shrink-0
                       ${isUser ? "bg-[#29B6E8]" : "bg-[#2D3A8C]"}`}
      >
        {isUser ? (
          <span className="text-white text-xs font-semibold">
            {getUser()?.username?.charAt(0).toUpperCase() || "U"}
          </span>
        ) : (
          <svg width="15" height="15" viewBox="0 0 40 40" fill="none">
            <path
              d="M8 32 L20 8 L32 32"
              fill="none"
              stroke="#29B6E8"
              strokeWidth="5"
              strokeLinecap="round"
            />
            <path d="M8 32 L20 21 L32 32" fill="#29B6E8" opacity="0.5" />
          </svg>
        )}
      </div>

      {/* Bulle */}
      <div className="max-w-[73%]">
        <div
          className={`px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap
          ${
            isUser
              ? "bg-[#2D3A8C] text-white rounded-2xl rounded-br-sm"
              : "bg-white text-gray-800 border border-[#D0DCF0] rounded-2xl rounded-bl-sm"
          }`}
        >
          {/* Fichiers joints — uniquement pour les messages utilisateur */}
          {isUser && <_Attachments attachments={message.attachments} />}

          {/* Texte du message */}
          {message.content}

          {/* Badges module + source — uniquement pour les messages assistant */}
          {!isUser && (message.module || message.source) && (
            <div className="flex gap-1.5 flex-wrap mt-3 pt-2.5 border-t border-[#E8EEF8]">
              {message.module && (
                <span
                  className="inline-flex items-center gap-1 bg-[#EAF2FC]
                                 border border-[#A8C8E8] rounded px-2 py-0.5
                                 text-xs text-[#1A4A8C]"
                >
                  <FiDatabase size={10} />
                  {message.module}
                </span>
              )}
              {message.source && (
                <span
                  className="inline-flex items-center gap-1 bg-[#F0F4FA]
                                 border border-[#C0CEDF] rounded px-2 py-0.5
                                 text-xs text-[#4A6080]"
                >
                  <FiFileText size={10} />
                  {message.source}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default MessageBubble;
