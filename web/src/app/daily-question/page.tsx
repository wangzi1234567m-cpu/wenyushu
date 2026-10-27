import type { Metadata } from "next";
import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";
import { DailyExplorer } from "@/features/daily/explorer";

export const metadata: Metadata = { title: "每日一问 · 问与书" };

export default function DailyQuestionPage() {
  return <><SiteHeader active="daily" /><main className="reading-page"><div className="page-heading"><p className="eyebrow">给好奇心留一点时间</p><h1>一个问题，一段新的思考。</h1><p>从此刻的直觉开始，也欢迎在讨论中改变想法。</p></div><DailyExplorer /></main><SiteFooter /></>;
}
