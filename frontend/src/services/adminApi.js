import { authHeader, getToken } from "./authApi";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function fetchDocuments() {
  const response = await fetch(`${API_BASE}/admin/documents`, {
    headers: authHeader(),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Erreur lors de la récupération des documents.");
  }

  return data;
}

export async function uploadDocument(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    };

    xhr.onload = () => {
      const data = JSON.parse(xhr.responseText);
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data);
      } else {
        reject(new Error(data.detail || "Erreur lors de l'upload."));
      }
    };

    xhr.onerror = () => reject(new Error("Erreur réseau lors de l'upload."));

    xhr.open("POST", `${API_BASE}/admin/upload`);
    xhr.setRequestHeader("Authorization", `Bearer ${getToken()}`);
    xhr.send(formData);
  });
}

export async function deleteDocument(filename) {
  const response = await fetch(
    `${API_BASE}/admin/documents/${encodeURIComponent(filename)}`,
    {
      method: "DELETE",
      headers: authHeader(),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Erreur lors de la suppression.");
  }

  return data;
}

export async function fetchHistory(skip = 0, limit = 20) {
  const response = await fetch(
    `${API_BASE}/admin/history?skip=${skip}&limit=${limit}`,
    { headers: authHeader() }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Erreur lors de la récupération de l'historique.");
  }

  return data;
}