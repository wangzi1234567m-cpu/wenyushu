"use client";

import { useEffect, useSyncExternalStore } from "react";
import { initializeSession, serverSnapshot, snapshot, subscribe } from "./store";

export function SessionStatus() {
  const state = useSyncExternalStore(subscribe, snapshot, serverSnapshot);
  useEffect(() => { void initializeSession(); }, []);
  return <div className="session" role="status" aria-live="polite">
    {state === "ready" ? "匿名访问已就绪" : state === "error" ?
      <>暂时无法连接。<button onClick={() => void initializeSession()}>重新连接</button></> : "正在建立匿名访问…"}
  </div>;
}
