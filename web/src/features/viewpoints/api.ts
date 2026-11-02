import { request } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type SavedViewpoint = components["schemas"]["SavedViewpoint"];
export type ViewpointExtraction = components["schemas"]["ViewpointExtraction"];
export type SavedPage = components["schemas"]["SavedViewpointPage"];
export type SaveSource = components["schemas"]["SavedViewpointCreate"];
export const sourceLabels = { user_quote: "用户原话", ai_viewpoint: "AI 观点 · 消息原文", ai_summary: "AI 提炼 · 非用户原话" };
// App Router navigation can mount the list while a save from the previous page is pending.
// Keep only in-flight promises in memory so that the next list observes those writes.
const pendingWrites = new Set<Promise<unknown>>();
function write<T>(operation: Promise<T>) {
  pendingWrites.add(operation);
  void operation.finally(() => pendingWrites.delete(operation)).catch(() => {});
  return operation;
}
export async function listSaved(offset = 0, conversation?: string, limit = 20) {
  await Promise.allSettled([...pendingWrites]);
  return request<SavedPage>(`/saved-viewpoints?offset=${offset}&limit=${limit}${conversation ? `&conversation_id=${encodeURIComponent(conversation)}` : ""}`, "GET");
}
export const saveViewpoint = (source: SaveSource) => write(request<SavedViewpoint>("/saved-viewpoints", "POST", source));
export const removeViewpoint = (id: string) => write(request<components["schemas"]["Ok"]>(`/saved-viewpoints/${id}`, "DELETE"));
export const getExtraction = (id: string) => request<ViewpointExtraction>(`/conversations/${id}/viewpoints`, "GET");
export const extractViewpoints = (id: string, upToSeq: number) => request<ViewpointExtraction>(`/conversations/${id}/viewpoints`, "POST", { up_to_seq: upToSeq }, undefined, false, 60000);
