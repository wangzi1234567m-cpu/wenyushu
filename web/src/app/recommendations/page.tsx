import Link from "next/link";
import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";

export default function RecommendationsPage() {
  return <><SiteHeader active="discover" /><main className="reading-page">
    <section className="hero"><span className="eyebrow">阅读的下一步</span><h1>让问题，成为阅读的起点。</h1>
      <p className="intro">推荐书籍功能正在准备中。你可以先回到讨论，把感兴趣的问题再展开一点。</p>
      <Link className="primary" href="/daily-question">返回原来的讨论</Link>
    </section></main><SiteFooter /></>;
}
