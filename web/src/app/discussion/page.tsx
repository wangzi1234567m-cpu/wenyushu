import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";
import { ArrowIcon } from "@/components/ui/line-icon";

export const metadata: Metadata = { title: "思辨助手 · 问与书" };

export default function DiscussionPage() {
  return <><SiteHeader active="discussion" /><main className="reading-page placeholder-page">
    <p className="eyebrow">把想法，再展开一点</p><h1>有些问题，值得慢慢聊。</h1>
    <p className="placeholder-description">独立思辨入口正在准备中。现在，你可以先进入每日一问，选择立场与理由，再与 AI 继续探讨。</p>
    <Link className="action-button" href="/daily-question">从每日一问聊起<ArrowIcon /></Link>
  </main><SiteFooter /></>;
}
