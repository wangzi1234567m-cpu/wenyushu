import Link from "next/link";

type Section = "home" | "daily" | "discover" | "discussion";
const navigation: { id: Section; label: string; href: string }[] = [
  { id: "home", label: "首页", href: "/" },
  { id: "daily", label: "每日一问", href: "/daily-question" },
  { id: "discover", label: "发现书籍", href: "/discover" },
  { id: "discussion", label: "思辨助手", href: "/discussion" },
];

export function SiteHeader({ active }: { active: Section }) {
  return <header className="site-header"><div className="site-header-inner">
    <Link className="site-wordmark" href="/" aria-label="问与书首页">问与书</Link>
    <span className="header-divider" aria-hidden="true" />
    <nav className="site-navigation" aria-label="主导航">{navigation.map((item) => <Link key={item.id} href={item.href} aria-current={active === item.id ? "page" : undefined}>{item.label}</Link>)}</nav>
    <Link className="site-search" href="/discover" aria-label="搜索书籍"><svg width="25" height="25" viewBox="0 0 28 28" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.4" /><path d="m18 18 7 7" stroke="currentColor" strokeWidth="1.4" /></svg></Link>
  </div></header>;
}
