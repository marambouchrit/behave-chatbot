import { useState, useEffect, useCallback } from "react";
import { FiPlus, FiTrash2, FiEdit2, FiCheck, FiX, FiMessageSquare } from "react-icons/fi";
import { fetchChats, createChat, renameChat, deleteChat } from "../services/api";
import { getUser, logout } from "../services/authApi";
import { useNavigate } from "react-router-dom";
import ChatWindow from "./ChatWindow";

function ChatLayout() {
  const [chats,        setChats]        = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [editingId,    setEditingId]    = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [isLoading,    setIsLoading]    = useState(true);
  const navigate = useNavigate();
  const user = getUser();

  // ── Chargement des chats ─────────────────────────────────────────────────

  const loadChats = useCallback(async () => {
    try {
      const data = await fetchChats();
      setChats(data.chats);
      return data.chats;
    } catch {
      return [];
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      try {
        const data = await fetchChats();
        setChats(data.chats);

        if (data.chats.length > 0) {
          setActiveChatId(data.chats[0].id);
        } else {
          const chat = await createChat("Nouvelle conversation");
          setChats([chat]);
          setActiveChatId(chat.id);
        }
      } catch {
        // Silencieux
      } finally {
        setIsLoading(false);
      }
    };

    init();
  }, []);

  // ── Nouveau chat ─────────────────────────────────────────────────────────

  const handleNewChat = useCallback(async () => {
    try {
      const chat = await createChat("Nouvelle conversation");
      setChats((prev) => [chat, ...prev]);
      setActiveChatId(chat.id);
    } catch {
    }
  }, []);



  const handleMessageSent = useCallback(async () => {
    const updatedChats = await loadChats();
    
    setActiveChatId((prev) => prev);
    setChats(updatedChats);
  }, [loadChats]);



  const handleDelete = async (chatId, e) => {
    e.stopPropagation();
    try {
      await deleteChat(chatId);
      const remaining = chats.filter((c) => c.id !== chatId);
      setChats(remaining);

      if (activeChatId === chatId) {
        if (remaining.length > 0) {
          setActiveChatId(remaining[0].id);
        } else {
          const newChat = await createChat("Nouvelle conversation");
          setChats([newChat]);
          setActiveChatId(newChat.id);
        }
      }
    } catch {
    }
  };

  // ── Renommage ────────────────────────────────────────────────────────────

  const handleStartRename = (chat, e) => {
    e.stopPropagation();
    setEditingId(chat.id);
    setEditingTitle(chat.title);
  };

  const handleConfirmRename = async (chatId) => {
    const title = editingTitle.trim();
    if (!title) return;
    try {
      const updated = await renameChat(chatId, title);
      setChats((prev) => prev.map((c) => (c.id === chatId ? updated : c)));
    } catch {
      
    } finally {
      setEditingId(null);
      setEditingTitle("");
    }
  };

  const handleCancelRename = () => {
    setEditingId(null);
    setEditingTitle("");
  };

  // ── Déconnexion ───────────────────────────────────────────────────────────

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  // ── Rendu ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen overflow-hidden">

      {/* ── Sidebar ── */}
      <div className="w-64 flex-shrink-0 bg-[#1E2A6E] flex flex-col">

        {/* Header sidebar */}
        <div className="px-4 py-4 border-b border-white/10">
          <div className="flex items-center gap-2 mb-4">
            <svg width="22" height="22" viewBox="0 0 40 40" fill="none">
              <path d="M8 32 L20 8 L32 32" fill="none" stroke="#29B6E8"
                strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M8 32 L20 21 L32 32" fill="#29B6E8" opacity="0.35"/>
            </svg>
            <span className="text-white text-sm font-semibold">BeHave Assistant</span>
          </div>

          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 bg-[#29B6E8]
                       hover:bg-[#1FA3D5] text-white text-sm font-medium py-2 px-3
                       rounded-lg transition-colors"
          >
            <FiPlus size={15} />
            Nouvelle conversation
          </button>
        </div>

        {/* Liste des chats */}
        <div className="flex-1 overflow-y-auto py-2">
          {isLoading ? (
            <div className="px-4 py-3 text-white/40 text-xs">Chargement...</div>
          ) : chats.length === 0 ? (
            <div className="px-4 py-3 text-white/40 text-xs">Aucune conversation</div>
          ) : (
            chats.map((chat) => (
              <div
                key={chat.id}
                onClick={() => setActiveChatId(chat.id)}
                className={[
                  "group flex items-center gap-2 px-3 py-2.5 mx-2 rounded-lg cursor-pointer",
                  "transition-colors duration-100",
                  activeChatId === chat.id
                    ? "bg-white/15 text-white"
                    : "text-white/60 hover:bg-white/8 hover:text-white/90",
                ].join(" ")}
              >
                <FiMessageSquare size={13} className="flex-shrink-0 opacity-60" />

                {editingId === chat.id ? (
                  <input
                    autoFocus
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter")  handleConfirmRename(chat.id);
                      if (e.key === "Escape") handleCancelRename();
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="flex-1 bg-white/10 text-white text-xs rounded px-1.5 py-0.5
                               outline-none border border-[#29B6E8] min-w-0"
                  />
                ) : (
                  <span className="flex-1 text-xs truncate">{chat.title}</span>
                )}

                <div
                  className={[
                    "flex items-center gap-1 flex-shrink-0",
                    editingId === chat.id ? "flex" : "hidden group-hover:flex",
                  ].join(" ")}
                  onClick={(e) => e.stopPropagation()}
                >
                  {editingId === chat.id ? (
                    <>
                      <button
                        onClick={() => handleConfirmRename(chat.id)}
                        className="text-green-400 hover:text-green-300 p-0.5"
                        title="Confirmer"
                      >
                        <FiCheck size={12} />
                      </button>
                      <button
                        onClick={handleCancelRename}
                        className="text-red-400 hover:text-red-300 p-0.5"
                        title="Annuler"
                      >
                        <FiX size={12} />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={(e) => handleStartRename(chat, e)}
                        className="text-white/40 hover:text-white/80 p-0.5"
                        title="Renommer"
                      >
                        <FiEdit2 size={12} />
                      </button>
                      <button
                        onClick={(e) => handleDelete(chat.id, e)}
                        className="text-white/40 hover:text-red-400 p-0.5"
                        title="Supprimer"
                      >
                        <FiTrash2 size={12} />
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="px-4 py-3 border-t border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-[#29B6E8] flex items-center
                            justify-center text-white text-xs font-semibold">
              {user?.username?.charAt(0).toUpperCase() || "U"}
            </div>
            <span className="text-white/70 text-xs truncate max-w-[90px]">
              {user?.username}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="text-white/40 hover:text-white/80 text-xs transition-colors"
            title="Se déconnecter"
          >
            Déconnexion
          </button>
        </div>
      </div>

      {/* ── Zone chat principale ── */}
      <div className="flex-1 min-w-0">
        {activeChatId ? (
          <ChatWindow
            chatId={activeChatId}
            onMessageSent={handleMessageSent}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Sélectionnez ou créez une conversation
          </div>
        )}
      </div>

    </div>
  );
}

export default ChatLayout;