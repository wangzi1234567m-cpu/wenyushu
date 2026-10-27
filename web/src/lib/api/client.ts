import { API_BASE } from "@/config/public";
import type { components } from "./schema";

type Session = components["schemas"]["SessionCreated"];
type ApiErrorBody = components["schemas"]["ErrorEnvelope"];
export class ApiError extends Error {
  constructor(public status: number, public detail: ApiErrorBody["error"]) {
    super(detail.message);
  }
}

let csrfToken: string | undefined;
export async function request<T>(path: string, method: string, body?: unknown, key?: string, refreshed = false): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method, credentials: "same-origin", cache: "no-store",
    headers: { ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(key ? { "Idempotency-Key": key } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) {
    let detail: ApiErrorBody["error"];
    try { detail = ((await response.json()) as ApiErrorBody).error; }
    catch { detail = { code: "NETWORK_ERROR", message: "暂时无法连接，请重试", retryable: true, request_id: "" }; }
    if (detail.code === "CSRF_REJECTED" && !refreshed && path !== "/auth/anonymous-session") {
      await bootstrapSession();
      return request<T>(path, method, body, key, true);
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export async function bootstrapSession(): Promise<Session> {
  const session = await request<Session>("/auth/anonymous-session", "POST");
  csrfToken = session.csrf_token;
  return session;
}

export async function revokeSession(): Promise<void> {
  await request<components["schemas"]["Ok"]>("/auth/anonymous-session", "DELETE");
  csrfToken = undefined;
}

export async function streamMessage(id: string, body: components["schemas"]["ConversationMessageCreate"],
  signal: AbortSignal, onEvent: (name: string, data: Record<string, unknown>) => void, refreshed = false): Promise<void> {
  const response = await fetch(`${API_BASE}/conversations/${id}/messages`, {
    method: "POST", credentials: "same-origin", cache: "no-store", signal,
    headers: { "Content-Type": "application/json", "Accept": "text/event-stream", ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json() as ApiErrorBody;
    if (payload.error.code === "CSRF_REJECTED" && !refreshed) {
      await bootstrapSession();
      return streamMessage(id, body, signal, onEvent, true);
    }
    throw new ApiError(response.status, payload.error);
  }
  if (!response.body || !response.headers.get("content-type")?.includes("text/event-stream")) throw new Error("Invalid stream");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "", completed = false;
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer = (buffer + decoder.decode(value, { stream: !done })).replace(/\r\n/g, "\n");
      let boundary: number;
      while ((boundary = buffer.indexOf("\n\n")) >= 0) {
        const block = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
        const lines = block.split("\n");
        const name = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
        const data = lines.filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trimStart()).join("\n");
        if (!name || !data) continue;
        const payload = JSON.parse(data) as Record<string, unknown>;
        if (name === "message_error") throw new ApiError(503, payload.error as ApiErrorBody["error"]);
        if (name === "message_completed") completed = true;
        onEvent(name, payload);
      }
      if (done) break;
    }
    if (!completed) throw new Error("Stream interrupted");
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
