import { useState, useEffect, useRef } from "react";
import Header        from "./Header";
import MessageBubble from "./MessageBubble";
import InputBar      from "./InputBar";
import Suggestions   from "./Suggestions";
import { sendMessage, resetHistory, checkHealth } from "../services/api";
import { getUser } from "../services/authApi";

const WELCOME_MESSAGE = {
  role: "assistant",
  content:
    "Bonjour ! Je suis BeHave Assistant.\n\nJe réponds à vos questions sur la suite BeHave en me basant sur la documentation officielle Siryos :\n● Predictive  ● Access  ● Master Data  ● Analytics\n\nComment puis-je vous aider ?",
};

const NO_ACTIVE_CHAT_MESSAGE = {
  role: "assistant",
  content: "Aucune conversation active. Créez ou sélectionnez un chat avant d'envoyer un message.",
};

// ---------------------------------------------------------------------------
// Helpers localStorage — clé par user + chatId
// ---------------------------------------------------------------------------

const _getStorageKey = (chatId) => {
  const user = getUser();
  return `behave_messages_${user?.username || "guest"}_${chatId}`;
};

const _saveMessages = (messages, chatId) => {
  if (chatId == null) return;
  const serializable = messages.map(({ attachments, ...rest }) => rest);
  localStorage.setItem(_getStorageKey(chatId), JSON.stringify(serializable));
};

const _loadMessages = (chatId) => {
  if (chatId == null) return [WELCOME_MESSAGE];
  const saved = localStorage.getItem(_getStorageKey(chatId));
  return saved ? JSON.parse(saved) : [WELCOME_MESSAGE];
};

const _clearMessages = (chatId) => {
  if (chatId == null) return;
  localStorage.removeItem(_getStorageKey(chatId));
};

// ---------------------------------------------------------------------------
// Normalise string (Suggestions) ou FormData (InputBar) → FormData
//
// chatId doit être résolu (non null/undefined) avant tout appel — vérifié
// par l'appelant (handleSend). Ici on ne fait que sérialiser sa valeur.
// ---------------------------------------------------------------------------

const _toFormData = (input, chatId) => {
  if (input instanceof FormData) {
    input.set("session_id", String(chatId));
    return input;
  }
  const fd = new FormData();
  fd.append("question",   input);
  fd.append("session_id", String(chatId));
  return fd;
};

// ---------------------------------------------------------------------------
// Construit les previews d'attachments pour affichage local
// ---------------------------------------------------------------------------

const _buildAttachments = (formData) => {
  const files = [...formData.getAll("files")];
  return files.map((file) => ({
    name: file.name,
    type: file.type,
    url:  null,
  }));
};

// ---------------------------------------------------------------------------
// Composant principal
// ---------------------------------------------------------------------------

/**
 * ChatWindow
 *
 * @param {number}   chatId         Identifiant du chat actif. Peut être null/undefined
 *                                  tant qu'aucun chat n'a été créé ou sélectionné —
 *                                  dans ce cas l'envoi de message est bloqué.
 * @param {function} onMessageSent  Callback appelé après chaque réponse reçue.
 *                                  Utilisé par ChatLayout pour rafraîchir la
 *                                  sidebar (auto-renommage du chat).
 */
function ChatWindow({ chatId, onMessageSent }) {
  const hasActiveChat = chatId != null;

  const [messages,  setMessages]  = useState(() => _loadMessages(chatId));
  const [isLoading, setIsLoading] = useState(false);
  const [isOnline,  setIsOnline]  = useState(true);
  const messagesEndRef = useRef(null);

  // Recharge les messages quand le chat actif change
  useEffect(() => {
    setMessages(_loadMessages(chatId));
  }, [chatId]);

  useEffect(() => { checkHealth().then(setIsOnline); }, []);

  useEffect(() => {
    _saveMessages(messages, chatId);
  }, [messages, chatId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // ── Envoi d'un message ──────────────────────────────────────────────────

  const handleSend = async (input) => {
    if (!hasActiveChat) {
      setMessages((prev) => [...prev, NO_ACTIVE_CHAT_MESSAGE]);
      return;
    }

    const formData = _toFormData(input, chatId);
    const question = formData.get("question");

    if (!question?.trim()) return;

    const attachments = _buildAttachments(formData);

    setMessages((prev) => [
      ...prev,
      {
        role:    "user",
        content: question,
        ...(attachments.length > 0 && { attachments }),
      },
    ]);
    setIsLoading(true);

    try {
      const result = await sendMessage(formData);
      setMessages((prev) => [
        ...prev,
        {
          role:    "assistant",
          content: result.content,
          module:  result.module,
          source:  result.source,
        },
      ]);
      setIsOnline(true);

      onMessageSent?.();

    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role:    "assistant",
          content: "Erreur de connexion. Vérifiez que le backend FastAPI tourne sur le port 8000.",
        },
      ]);
      setIsOnline(false);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Reset du chat courant ───────────────────────────────────────────────

  const handleReset = async () => {
    if (!hasActiveChat) return;
    await resetHistory(String(chatId));
    _clearMessages(chatId);
    setMessages([WELCOME_MESSAGE]);
  };

  return (
    <div className="flex flex-col h-screen bg-[#EEF2F7]">
      <Header onReset={handleReset} isOnline={isOnline} />

      <Suggestions onSelect={handleSend} isLoading={isLoading} />

      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-2">
        {messages.map((msg, index) => (
          <MessageBubble key={index} message={msg} />
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-gray-400 text-sm px-2">
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-2 h-2 bg-[#29B6E8] rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
            BeHave réfléchit...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <InputBar
        onSend={handleSend}
        isLoading={isLoading}
        sessionId={hasActiveChat ? String(chatId) : undefined}
      />
    </div>
  );
}

export default ChatWindow;