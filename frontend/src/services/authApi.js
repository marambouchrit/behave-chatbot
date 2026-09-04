const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "behave_token";
const USER_KEY  = "behave_user";

// ---------------------------------------------------------------------------
// Gestion du token et de l'utilisateur
// ---------------------------------------------------------------------------

export function saveAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser() {
  const user = localStorage.getItem(USER_KEY);
  return user ? JSON.parse(user) : null;
}

export function removeAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAuthenticated() {
  return Boolean(getToken());
}

export function isAdmin() {
  const user = getUser();
  return user?.role === "admin";
}

export function authHeader() {
  return { Authorization: `Bearer ${getToken()}` };
}

// ---------------------------------------------------------------------------
// Endpoints auth
// ---------------------------------------------------------------------------

export async function login(username, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Identifiants incorrects.");
  }

  saveAuth(data.access_token, {
    id:       data.id,
    username: data.username,
    role:     data.role,
  });

  return data;
}

export async function register(username, password) {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Erreur lors de l'inscription.");
  }

  return data;
}

export async function verifyToken() {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: authHeader(),
  });

  if (!response.ok) {
    removeAuth();
    throw new Error("Session expirée. Veuillez vous reconnecter.");
  }

  return response.json();
}

export function logout() {
  removeAuth();
}