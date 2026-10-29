const API_BASE = "http://localhost:8000";

function getToken() {
  return localStorage.getItem("token");
}
function getUser() {
  try { return JSON.parse(localStorage.getItem("user") || "null"); } catch { return null; }
}
function setAuth(token, user) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
}
function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

async function request(path, { method = "GET", body = null, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const t = getToken();
    if (!t) throw { status: 401, detail: "未登录" };
    headers["Authorization"] = `Bearer ${t}`;
  }
  const res = await fetch(API_BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  const text = await res.text();
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const detail = (data && data.detail) || `请求失败 (${res.status})`;
    throw { status: res.status, detail: typeof detail === "string" ? detail : JSON.stringify(detail) };
  }
  return data;
}

const api = {
  register: (u, p) => request("/api/auth/register", { method: "POST", body: { username: u, password: p } }),
  login: (u, p) => request("/api/auth/login", { method: "POST", body: { username: u, password: p } }),
  me: () => request("/api/auth/me", { auth: true }),
  listSurveys: () => request("/api/surveys"),
  mySurveys: () => request("/api/surveys/mine", { auth: true }),
  getSurvey: (id) => request(`/api/surveys/${id}`, { auth: !!getToken() }),
  createSurvey: (payload) => request("/api/surveys", { method: "POST", body: payload, auth: true }),
  submit: (id, answers) => request(`/api/surveys/${id}/submit`, { method: "POST", body: { answers }, auth: !!getToken() }),
  stats: (id) => request(`/api/surveys/${id}/stats`, { auth: true }),
  deleteSurvey: (id) => request(`/api/surveys/${id}`, { method: "DELETE", auth: true }),
  // 题目库
  listBank: () => request("/api/question-bank", { auth: true }),
  saveBank: (question, name) => request("/api/question-bank", { method: "POST", body: { question, name }, auth: true }),
  deleteBank: (id) => request(`/api/question-bank/${id}`, { method: "DELETE", auth: true }),
  shareBank: (id, username) => request(`/api/question-bank/${id}/share`, { method: "POST", body: { username }, auth: true }),
  duplicateSurvey: (id) => request(`/api/surveys/${id}/duplicate`, { method: "POST", auth: true }),
  updateBank: (id, question, name) => request(`/api/question-bank/${id}`, { method: "PUT", body: { question, name }, auth: true }),
  bankHistory: (id) => request(`/api/question-bank/${id}/history`, { auth: true }),
  bankHistoryVersion: (id, version) => request(`/api/question-bank/${id}/history/${version}`, { auth: true }),
  restoreBank: (id, version) => request(`/api/question-bank/${id}/restore/${version}`, { method: "POST", auth: true }),
  copyBank: (id, name) => request(`/api/question-bank/${id}/copy`, { method: "POST", body: name ? { name } : {}, auth: true }),
  bankUsages: (id) => request(`/api/question-bank/${id}/usages`, { auth: true }),
  bankStats: (id) => request(`/api/question-bank/${id}/stats`, { auth: true }),
};