import Link from "next/link";

export default function RecommendationsPage() {
  return <main><header><Link className="brand" href="/">问与书<span>QUESTION &amp; BOOK</span></Link><span className="edition">带着问题，继续阅读</span></header>
    <section className="hero"><span className="eyebrow">阅读的下一步</span><h1>让问题，成为阅读的起点。</h1>
      <p className="intro">推荐书籍功能正在准备中。你可以先回到讨论，把感兴趣的问题再展开一点。</p>
      <Link className="primary" href="/#daily-question">返回原来的讨论</Link>
    </section></main>;
}
