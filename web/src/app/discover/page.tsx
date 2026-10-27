import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";
import { discoveryEntries } from "@/features/home/book-discovery-entry";
import { ArrowIcon } from "@/components/ui/line-icon";

export const metadata: Metadata = { title: "发现书籍 · 问与书" };

export default async function DiscoverPage({ searchParams }: { searchParams: Promise<{ mode?: string }> }) {
  const { mode } = await searchParams;
  const selected = discoveryEntries.find((entry) => entry.mode === mode);
  return <><SiteHeader active="discover" /><main className="reading-page placeholder-page">
    <p className="eyebrow">阅读的下一步</p><h1>{selected?.title ?? "下一本书，从好奇心开始。"}</h1>
    <p className="placeholder-description">{selected ? `${selected.title}正在准备中。` : "书籍发现功能正在准备中。"}我们期待让每一份兴趣、疑问和学习目标，都找到值得展开的阅读。</p>
    <nav className="discovery-tabs" aria-label="找书方式">{discoveryEntries.map((entry) => <Link key={entry.mode} href={`/discover?mode=${entry.mode}`} aria-current={selected?.mode === entry.mode ? "page" : undefined}>{entry.title}</Link>)}</nav>
    <p className="note">这里暂不提供书籍检索或推荐。你可以先从每日一问开始思考。</p>
    <Link className="action-button" href="/daily-question">进入每日一问<ArrowIcon /></Link>
  </main><SiteFooter /></>;
}
