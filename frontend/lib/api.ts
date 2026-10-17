export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Doc = { id: string; filename: string; status: string; error: string | null; n_pages: number; n_chunks: number };
export type Citation = { ref: number; document_id: string; filename: string; page: number; text: string; score: number };
export type ChatResult = {
  answer: string; provider: string; model: string; citations: Citation[];
  retrieval_ms: number; generation_ms: number; prompt_tokens: number; completion_tokens: number;
};

export const getToken = () => (typeof window === "undefined" ? null : localStorage.getItem("token"));
export const setToken = (t: string | null) => (t ? localStorage.setItem("token", t) : localStorage.removeItem("token"));

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (res.status === 401) { setToken(null); if (typeof window !== "undefined") window.location.href = "/"; }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const json = (body: unknown): RequestInit => ({
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});
