"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { extractViewpoints, getExtraction, listSaved, removeViewpoint, saveViewpoint, type SaveSource, type SavedViewpoint, type ViewpointExtraction } from "./api";

export function useSavedViewpoints(conversationId?: string) {
  const [saved, setSaved] = useState<SavedViewpoint[]>([]);
  const [error, setError] = useState("");
  const [working, setWorking] = useState<string[]>([]);
  const refresh = useCallback(async () => {
    if (!conversationId) return;
    setError("");
    const all: SavedViewpoint[] = []; let offset: number | null = 0;
    while (offset !== null) { const page = await listSaved(offset, conversationId, 100); all.push(...page.items); offset = page.next_offset; }
    setSaved(all);
  }, [conversationId]);
  useEffect(() => {
    const timer = setTimeout(() => { void refresh().catch(() => setError("收藏状态暂时无法加载，可以稍后重试。")); }, 0);
    return () => clearTimeout(timer);
  }, [refresh]);
  async function toggle(key: string, source: SaveSource, existing?: SavedViewpoint) {
    setError(""); setWorking((old) => [...old, key]);
    try {
      if (existing) { await removeViewpoint(existing.id); setSaved((old) => old.filter((item) => item.id !== existing.id)); }
      else { const item = await saveViewpoint(source); setSaved((old) => [...old.filter((v) => v.id !== item.id), item]); }
    } catch (reason) { setError(reason instanceof ApiError ? reason.message : "收藏未能保存，请稍后重试。"); }
    finally { setWorking((old) => old.filter((item) => item !== key)); }
  }
  return { saved, error, working, toggle, refresh };
}

export function ViewpointCandidates({ conversationId, upToSeq, busy, collection }: { conversationId: string; upToSeq: number; busy: boolean; collection: ReturnType<typeof useSavedViewpoints> }) {
  const [batch, setBatch] = useState<ViewpointExtraction>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => { void getExtraction(conversationId).then(setBatch).catch(() => setError("已提炼观点暂时无法加载，请重试。")); }, 0);
    return () => clearTimeout(timer);
  }, [conversationId]);
  useEffect(() => {
    if (batch?.status !== "processing") return;
    const timer = setInterval(() => { void getExtraction(conversationId).then(setBatch).catch(() => setError("提炼状态暂时无法读取。")); }, 2000);
    return () => clearInterval(timer);
  }, [batch?.status, conversationId]);
  async function extract() {
    setLoading(true); setError("");
    try { setBatch(await extractViewpoints(conversationId, upToSeq)); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "观点提炼暂时中断，可以稍后重试。"); }
    finally { setLoading(false); }
  }
  const current = batch?.status === "succeeded" && batch.up_to_seq === upToSeq;
  return <section className="viewpoint-section" aria-label="讨论观点">
    <div className="viewpoint-heading"><h4>留住值得回味的想法</h4><Link href="/saved-viewpoints">我的收藏</Link></div>
    <p className="note">按需整理最近几轮讨论，不自动收藏。AI 的提炼可能不完整，请核对是否符合原意。</p>
    <button className="viewpoint-extract" disabled={busy || loading || !upToSeq || batch?.status === "processing" || current} onClick={() => void extract()}>{loading || batch?.status === "processing" ? "正在提炼观点…" : current ? "已提炼这段讨论" : "提炼最近讨论的观点"}</button>
    {error && <p role="alert" className="error">{error}</p>}
    {batch?.status === "failed" && !loading && <p className="note">上次提炼未完成，可以重试。原有讨论不受影响。</p>}
    {batch?.status === "succeeded" && batch.items.length === 0 && <p className="note">这一段暂时没有值得单独提炼的观点。可以继续聊，也可以直接收藏消息原文。</p>}
    {batch && batch.up_to_seq < upToSeq && batch.items.length > 0 && <p className="note">以下来自前面一段讨论，可按需整理新的内容。</p>}
    {batch?.items.map((item, index) => {
      const existing = collection.saved.find((saved) => saved.id === item.viewpoint_id);
      return <article className="viewpoint-card" key={item.viewpoint_id}><span className="viewpoint-label">AI 提炼 · 非用户原话</span><p>{item.content}</p><button aria-pressed={!!existing} disabled={collection.working.includes(item.viewpoint_id)} onClick={() => void collection.toggle(item.viewpoint_id, { conversation_id: conversationId, extraction_id: batch.extraction_id!, item_index: index }, existing)}>{existing ? "已收藏 · 取消收藏" : "收藏观点"}</button></article>;
    })}
  </section>;
}
