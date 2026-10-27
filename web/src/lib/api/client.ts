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
export async function request<T>(path: string, method: string, body?: unknown, key?: string): Promise<T> {
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
