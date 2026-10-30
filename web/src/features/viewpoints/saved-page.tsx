"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { initializeSession } from "@/features/session/store";
import { ApiError } from "@/lib/api/client";
import { listSaved, removeViewpoint, sourceLabels, type SavedPage } from "./api";

export function SavedViewpoints() {
  const [page, setPage] = useState<SavedPage>();
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState("");
  const [error, setError] = useState("");
  async function load(next = offset) {
    setLoading(true); setError("");
    try { await initializeSession(); setPage(await listSaved(next)); setOffset(next); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "收藏暂时无法加载，请重试。"); }
    finally { setLoading(false); }
  }
  useEffect(() => { const timer = setTimeout(() => { void load(0); }, 0); return () => clearTimeout(timer); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  async function remove(id: string) {
    setRemoving(id); setError("");
    try { await removeViewpoint(id); await load(0); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "取消收藏未能完成，请重试。"); }
    finally { setRemoving(""); }
  }
  return <section aria-label="观点收藏" className="saved-viewpoints">
    <p className="note">收藏属于当前浏览器的匿名身份。删除原讨论时，关联收藏也会一并清理。</p>
    {loading && <p role="status">正在加载收藏…</p>}
    {error && <div role="alert" className="error"><p>{error}</p><button disabled={loading} onClick={() => void load()}>重新加载收藏</button></div>}
    {!loading && !error && page?.items.length === 0 && <div className="collection-empty"><h2>还没有收藏的观点。</h2><p>讨论中遇到值得回味的话，可以把它留在这里。</p><Link className="text-action" href="/daily-question">从一个问题开始</Link></div>}
    {page?.items.map((item) => <article className="saved-viewpoint" key={item.id}>
      <div className="viewpoint-meta"><span className="viewpoint-label">{sourceLabels[item.source_type]}</span><time dateTime={item.created_at}>{new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", dateStyle: "medium", timeStyle: "short" }).format(new Date(item.created_at))}</time></div>
      <h2>{item.topic_title}</h2><p className="saved-content">{item.content}</p>
      <div className="viewpoint-actions">{item.source_available ? <Link href={`/discussion/${item.conversation_id}${item.message_id ? `?message_id=${item.message_id}` : ""}`}>返回原讨论</Link> : <span className="note">原讨论已不可用</span>}
        <button disabled={loading || removing === item.id} onClick={() => void remove(item.id)}>{removing === item.id ? "正在取消…" : "取消收藏"}</button></div>
    </article>)}
    {page && <nav className="collection-pagination" aria-label="收藏分页"><button disabled={loading || offset === 0} onClick={() => void load(Math.max(0, offset - 20))}>上一页</button><button disabled={loading || page.next_offset === null} onClick={() => void load(page.next_offset!)}>下一页</button></nav>}
  </section>;
}
