export function ArrowIcon({ className = "" }: { className?: string }) {
  return <svg className={className} width="28" height="16" viewBox="0 0 28 16" fill="none" aria-hidden="true"><path d="M1 8h25M20 2l6 6-6 6" stroke="currentColor" strokeWidth="1.2" /></svg>;
}

export function DiscoveryIcon({ kind }: { kind: "interest" | "question" | "learning" }) {
  return <svg width="42" height="42" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {kind === "interest" ? <><path d="M24 12c-5-4-12-4-18-2v28c6-2 13-2 18 2 5-4 12-4 18-2V10c-6-2-13-2-18 2Z" /><path d="M24 12v28M10 11v23c5-1 9 0 14 3M38 11v23c-5-1-9 0-14 3" /></> : kind === "question" ? <><circle cx="24" cy="25" r="16" /><path d="m16 34 5-13 13-7-6 13-12 7ZM24 4v5M24 2v2M36 8l-4 5" /></> : <><path d="M9 40V28h5v12M22 40V18h5v22M35 40V8h5v32M6 40h2M44 40h-1" /></>}
  </svg>;
}
