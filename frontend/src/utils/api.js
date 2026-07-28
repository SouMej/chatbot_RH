const API_URL = "http://localhost:8000";

export function saveToken(token) {
  localStorage.setItem("docurh-token", token);
}

export function getToken() {
  return localStorage.getItem("docurh-token");
}

export function clearToken() {
  localStorage.removeItem("docurh-token");
}

export function isLoggedIn() {
  return !!getToken();
}

async function handleResponse(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // FastAPI a deux formats d'erreur differents :
    // - erreurs "metier" (401, 403, 409...) -> detail est une simple chaine
    // - erreurs de validation Pydantic (422) -> detail est une liste d'objets
    //   du type { msg: "...", loc: [...], type: "..." }
    let message = "Une erreur est survenue.";
    if (typeof data.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data.detail)) {
      message = data.detail.map((e) => e.msg).join(" ");
    }
    throw new Error(message);
  }
  return data;
}

export async function registerRequest(nom, email, password) {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nom, email, password }),
  });
  return handleResponse(res);
}

export async function loginRequest(email, password) {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return handleResponse(res);
}

export async function verifyEmailRequest(token) {
  const res = await fetch(`${API_URL}/auth/verify/${token}`);
  return handleResponse(res);
}

export async function getCurrentUser() {
  const res = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  return handleResponse(res);
}

export async function logoutRequest() {
  const res = await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  clearToken();
  return handleResponse(res).catch(() => {});
}

export async function chatRequest(question, conversationId = null) {
  const payload = { question };
  if (conversationId) {
    payload.conversation_id = conversationId;
  }
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function getChatHistory() {
  const res = await fetch(`${API_URL}/chat/history`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  return handleResponse(res);
}

export async function getConversations() {
  const res = await fetch(`${API_URL}/chat/conversations`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  return handleResponse(res);
}

export async function deleteConversationRequest(conversationId) {
  const res = await fetch(`${API_URL}/chat/conversations/${conversationId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  return handleResponse(res);
}
