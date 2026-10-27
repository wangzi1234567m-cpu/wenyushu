import { SessionStatus } from "@/features/session/status";

export function SiteFooter() {
  return <footer className="site-footer">
    <p className="footer-signature"><span aria-hidden="true" />问与书 · 阅读与思辨<span aria-hidden="true" /></p>
    <div className="footer-meta"><span>信息时代一方阅读与思考的净土</span><SessionStatus /></div>
  </footer>;
}
