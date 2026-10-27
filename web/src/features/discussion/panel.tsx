"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ApiError, request, streamMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

type Message = components["schemas"]["ConversationMessage"];
type Conversation = components["schemas"]["Conversation"];
type Draft = components["schemas"]["ConversationMessageCreate"];

export function DiscussionPanel({ explorationId }: { explorationId: string }) {
  const [conversation, setConversation] = useState<Conversation>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [retry, setRetry] = useState<Draft>();
  const controller = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const mounted = useRef(true);

  function fail(reason: unknown) { setError(reason instanceof ApiError ? reason.message : "回复暂时中断，已完成的消息会保留。可以重试或继续表达。"); }
  async function history(id: string) {
    let after = 0;
    const all: Message[] = [];
    while (true) {
      const page = await request<components["schemas"]["ConversationMessagePage"]>(`/conversations/${id}/messages?after_seq=${after}&limit=100`, "GET");
      all.push(...page.messages);
      if (page.next_after_seq === null) break;
      after = page.next_after_seq;
    }
    setMessages(all);
    return all;
  }
  async function send(id: string, draft: Draft) {
    setBusy(true); setError(""); setRetry(draft);
    const abort = new AbortController(); controller.current = abort;
    const timeout = setTimeout(() => abort.abort(), 185000);
    try {
      await streamMessage(id, draft, abort.signal, (name, payload) => {
        if (name === "message_started") {
          const assistant: Message = { id: String(payload.message_id), seq: Number(payload.seq), role: "assistant", status: "generating", content: "", created_at: new Date().toISOString() };
          setMessages((old) => {
            const user: Message = { ...assistant, id: `local-${draft.client_message_id}`, seq: assistant.seq - 1, role: "user", status: "completed", content: draft.content };
            return [...old.filter((m) => m.seq < user.seq), user, assistant];
          });
        }
        if (name === "message_delta") setMessages((old) => old.map((m) => m.id === payload.message_id ? { ...m, content: m.content + String(payload.delta) } : m));
        if (name === "message_completed") setMessages((old) => old.map((m) => m.id === payload.message_id ? { ...m, status: "completed" } : m));
      });
      setRetry(undefined);
    } catch (reason) {
      if (abort.signal.aborted) setError("已停止等待回复。已完成的消息会保留，稍后可刷新状态或继续讨论。");
      else fail(reason);
    } finally {
      clearTimeout(timeout); controller.current = null;
      try { await history(id); } catch { /* Preserve the visible messages when reconnecting fails. */ }
      setBusy(false);
    }
  }
  async function load() {
    setError("");
    try {
      const value = await request<Conversation>("/conversations", "POST", { kind: "discussion", topic_id: null, exploration_id: explorationId });
      if (!mounted.current) return;
      setConversation(value);
      const rows = await history(value.conversation_id); setReady(true);
      if (!rows.length && mounted.current) await send(value.conversation_id, { client_message_id: "opening", content: "我已选择立场和理由，请从这里开始讨论。" });
    } catch (reason) { fail(reason); }
  }
  useEffect(() => {
    mounted.current = true;
    const timer = setTimeout(() => { void load(); }, 0);
    return () => { mounted.current = false; clearTimeout(timer); controller.current?.abort(); };
  }, [explorationId]); // eslint-disable-line react-hooks/exhaustive-deps
  const generating = messages.some((m) => m.status === "generating");
  useEffect(() => {
    if (busy || !generating || !conversation) return;
    const timer = setInterval(() => { void history(conversation.conversation_id).catch(fail); }, 2000);
    return () => clearInterval(timer);
  }, [busy, generating, conversation]);
  useEffect(() => { if (busy) end.current?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, [messages, busy]);

  return <div className="discussion-layout">
    <section className="discussion" aria-label="持续讨论">
      <div className="discussion-title"><h3>把想法再展开一点</h3><span className="soon">{conversation?.provider_mode === "mock" ? "AI 演示 · Mock" : "AI 生成 · DeepSeek"}</span></div>
      <p className="note">可以赞同、反驳，也可以改变主意。AI 回复可能有误，请保留自己的判断。</p>
      <div className="messages" aria-live="polite" aria-busy={busy}>
        {messages.map((message) => <article key={message.id} className={`message ${message.role}`}>
          <span className="message-role">{message.role === "user" ? "你" : "问与书 · AI"}</span>
          <p>{message.content || (message.status === "generating" ? "正在思考…" : "这次回复未完成。你可以继续表达。")}</p>
          {message.status === "failed" && <small>回复中断</small>}
        </article>)}<div ref={end} />
      </div>
      {error && <p role="alert" className="error">{error}</p>}
      {!ready && <button onClick={() => void load()}>重新连接讨论</button>}
      {retry && !busy && <button onClick={() => conversation && void send(conversation.conversation_id, retry)}>重试上一条消息</button>}
      <form onSubmit={(event) => {
        event.preventDefault(); if (!conversation || !text.trim() || busy || generating) return;
        const draft = { client_message_id: crypto.randomUUID(), content: text.trim() }; setText(""); void send(conversation.conversation_id, draft);
      }}>
        <label className="supplement" htmlFor="discussion-input">继续说说你的想法</label>
        <textarea id="discussion-input" maxLength={4000} value={text} onChange={(event) => setText(event.target.value)} disabled={!ready} />
        <div className="composer-actions"><span className="count">{Array.from(text).length}/4000</span>
          {busy ? <button type="button" onClick={() => controller.current?.abort()}>停止回复</button> : <button className="primary" disabled={!ready || !text.trim() || generating}>发送</button>}
        </div>
      </form>
    </section>
    <aside className="reading-side"><span className="eyebrow">让阅读延续思考</span><h3>带着这个问题，走向一本书</h3><p>聊到这里，如果你想从阅读中继续探索，可以随时前往找书页面。</p>
      {conversation && <Link className="primary" href={`/recommendations?conversation_id=${encodeURIComponent(conversation.conversation_id)}`}>根据讨论推荐书</Link>}
      <p className="note">找书功能正在准备中，当前不会发起检索。</p>
    </aside>
  </div>;
}
