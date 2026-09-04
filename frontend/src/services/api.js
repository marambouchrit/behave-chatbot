import { authHeader } from "./authApi";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// ─── Helper interne ────────────────────────────────────────────────────────

async function _request(path, options = {}) {
  const { headers: extraHeaders, ...restOptions } = options;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...restOptions,
    headers: {
      ...authHeader(),
      ...(extraHeaders || {}),
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Erreur API : ${response.status}`);
  }
  return response.json();
}

// ─── RAG ──────────────────────────────────────────────────────────────────

export async function sendMessage(formData) {
  const data = await _request("/chat", {
    method: "POST",
    body: formData,
  });
  return {
    content: data.answer,
    module:  data.module,
    source:  data.source,
  };
}

export async function resetHistory(sessionId) {
  await _request(`/history?session_id=${sessionId}`, { method: "DELETE" });
}

export async function checkHealth() {
  try {
    const data = await _request("/health");
    return data.status === "ok";
  } catch {
    return false;
  }
}

// ─── Chats ────────────────────────────────────────────────────────────────

export async function fetchChats() {
  return _request("/chats");
}

export async function createChat(title = "Nouvelle conversation") {
  return _request("/chats", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ title }),
  });
}

export async function renameChat(chatId, newTitle) {
  return _request(`/chats/${chatId}`, {
    method:  "PATCH",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ title: newTitle }),
  });
}

export async function deleteChat(chatId) {
  return _request(`/chats/${chatId}`, { method: "DELETE" });
}