"use client";

import { useEffect, useRef, useState } from "react";
import { initializeSession } from "@/features/session/store";
import { ApiError } from "@/lib/api/client";
import { createExploration, getDaily, getExploration, getJob, recommend, submitAnswer, type Answer, type DailyQuestion, type Exploration, type Job } from "./api";

const SLOT = "wqs.daily.exploration";
type Saved = { id: string; version: string; title: string; intro: string; job?: string; key?: string; revisionSource?: string; revisionIndex?: number };

export function DailyExplorer() {
  const [daily, setDaily] = useState<DailyQuestion>();
  const [state, setState] = useState<Exploration>();
  const [saved, setSaved] = useState<Saved>();
  const [job, setJob] = useState<Job>();
  const [selection, setSelection] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState<Answer[]>();
  const pendingKey = useRef("");

  function persist(value: Saved) { setSaved(value); sessionStorage.setItem(SLOT, JSON.stringify(value)); }
  function present(value: Exploration) { setState(value); setSelection(""); setText(""); }
  function fail(reason: unknown) {
    setError(reason instanceof ApiError ? reason.message : "暂时无法连接，请重试。你的已提交答案会保留。");
  }
  async function load() {
    setError(""); setBusy(true);
    try {
      await initializeSession();
      setDaily(await getDaily());
      const raw = sessionStorage.getItem(SLOT);
      if (raw) {
        const value: Saved = JSON.parse(raw);
        try {
          present(await getExploration(value.id)); setSaved(value);
          if (value.revisionSource && value.revisionIndex !== undefined) {
            const previous = await getExploration(value.revisionSource);
            setRevision((previous.answers ?? []).slice(0, value.revisionIndex).map((entry) => ({
              step_id: entry.step_id, option_id: entry.option_id, supplementary_text: entry.supplementary_text,
            })));
          }
          if (value.job) setJob(await getJob(value.job));
          pendingKey.current = value.key ?? "";
        } catch (reason) {
          if (reason instanceof ApiError && [401, 404].includes(reason.status)) sessionStorage.removeItem(SLOT);
          else throw reason;
        }
      }
    } catch (reason) { fail(reason); } finally { setBusy(false); }
  }
  useEffect(() => {
    const timer = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(timer);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function start() {
    if (!daily) return;
    setBusy(true); setError("");
    try {
      const value = await createExploration(daily.question_version_id);
      persist({ id: value.exploration_id, version: value.question_version_id, title: daily.title, intro: daily.intro });
      present(value); setJob(undefined); setRevision(undefined); pendingKey.current = "";
    } catch (reason) { fail(reason); } finally { setBusy(false); }
  }
  async function answer() {
    if (!state?.next_step || !selection) return;
    setBusy(true); setError("");
    try {
      present(await submitAnswer(state.exploration_id, { step_id: state.next_step.id, option_id: selection, supplementary_text: text.trim() || null }));
    } catch (reason) { fail(reason); } finally { setBusy(false); }
  }
  async function revise(index: number) {
    if (!state || !saved) return;
    const prefix = (state.answers ?? []).slice(0, index).map((entry) => ({
      step_id: entry.step_id, option_id: entry.option_id, supplementary_text: entry.supplementary_text,
    }));
    setBusy(true); setError("");
    try {
      const fresh = await createExploration(state.question_version_id);
      persist({ id: fresh.exploration_id, version: fresh.question_version_id, title: saved.title, intro: saved.intro,
        revisionSource: state.exploration_id, revisionIndex: index });
      setJob(undefined); pendingKey.current = ""; present(fresh);
      setRevision(prefix);
    } catch (reason) { fail(reason); } finally { setBusy(false); }
  }
  async function replay() {
    if (!state || !revision) return;
    setBusy(true); setError("");
    try {
      let value = state;
      for (const entry of revision) value = await submitAnswer(state.exploration_id, entry);
      present(value); setRevision(undefined);
      if (saved) persist({ id: saved.id, version: saved.version, title: saved.title, intro: saved.intro });
    } catch (reason) { fail(reason); } finally { setBusy(false); }
  }
  async function findBooks() {
    if (!state?.reading_intent_id || !saved) return;
    setBusy(true); setError("");
    try {
      const key = pendingKey.current || crypto.randomUUID(); pendingKey.current = key;
      persist({ ...saved, key });
      const result = await recommend(state.reading_intent_id, key);
      setJob(result); persist({ ...saved, key, job: result.job_id });
    } catch (reason) { fail(reason); } finally { setBusy(false); }
  }
  async function resumeCompletion() {
    const last = state?.answers?.at(-1);
    if (!state || !last) return;
    setBusy(true); setError("");
    try { present(await submitAnswer(state.exploration_id, { step_id: last.step_id,
      option_id: last.option_id, supplementary_text: last.supplementary_text })); }
    catch (reason) { fail(reason); } finally { setBusy(false); }
  }
  return <section className="daily" id="daily-question" aria-label="每日一问">
    <div className="daily-heading"><span className="eyebrow">每日一问 · {daily?.local_date ?? "正在加载"}</span><span className="soon">固定样例推荐</span></div>
    <h2>{saved?.title ?? daily?.title ?? "正在准备今日问题…"}</h2>
    <p>{saved?.intro ?? daily?.intro}</p>
    {error && <p role="alert" className="error">{error}</p>}
    {!daily && <button disabled={busy} onClick={() => void load()}>重新加载</button>}
    {!state && daily && <button className="primary" disabled={busy} onClick={() => void start()}>开始探索</button>}
    {state && <>
      <ol className="answers">{(state.answers ?? []).map((entry, index) => <li key={entry.step_id}>
        <span>{entry.step_prompt}<br />{entry.option_label ?? "已选择"}{entry.supplementary_text ? ` · ${entry.supplementary_text}` : ""}</span>
        <button disabled={busy} onClick={() => void revise(index)}>修改第 {index + 1} 步</button>
      </li>)}</ol>
      {revision ? <div><p>已建立同版本新探索。确认后恢复仍然有效的前面答案。</p><button disabled={busy} onClick={() => void replay()}>恢复前面的答案</button></div> : state.next_step && <fieldset disabled={busy}>
        <legend>{state.next_step.prompt}</legend>
        <div className="options">{state.next_step.options.map((option) => <label key={option.id} className={selection === option.id ? "selected" : ""}>
          <input type="radio" name={state.next_step!.id} value={option.id} checked={selection === option.id} onChange={() => setSelection(option.id)} />{option.label}
        </label>)}</div>
        <label className="supplement">也可以补充你的想法（可选，最多 300 字符）<textarea maxLength={300} value={text} onChange={(event) => setText(event.target.value)} /></label>
        <span className="count">{Array.from(text).length}/300</span>
        <button className="primary" disabled={!selection || busy} onClick={() => void answer()}>继续</button>
      </fieldset>}
      {state.status === "completed" && <div className="completion"><p>已整理你的阅读方向。点击后才会生成书单。</p><button className="primary" disabled={busy} onClick={() => void findBooks()}>根据这些想法找书</button></div>}
      {state.status === "expired" && <p>这次探索已过期，可以重新开始。</p>}
      {!state.next_step && state.status === "active" && <div><p>阅读方向关联尚未完成，已提交答案会保留。</p><button disabled={busy} onClick={() => void resumeCompletion()}>恢复阅读方向</button></div>}
      <button disabled={busy} onClick={() => void start()}>从今日问题重新开始</button>
    </>}
    {job && <section className="book-results" aria-label="推荐书单"><h3>沿着问题，继续阅读</h3><p>当前为固定样例推荐，补充文字尚未进行 AI 语义分析。</p>
      {job.error && <p role="alert">{job.error.message}</p>}
      {job.items.map((book) => <article className="book" key={book.work_id}><h3>{book.title}</h3><p>{book.author}</p><p>{book.summary}</p><p>{book.recommendation_reason}</p>
        {book.evidence_urls.map((url) => <a key={url} href={url} target="_blank" rel="noreferrer">查看书目来源</a>)}
      </article>)}
    </section>}
    <span role="status" className="operation-status">{busy ? "正在保存与加载…" : ""}</span>
  </section>;
}
