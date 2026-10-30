import type { Metadata } from "next";
import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";
import { SavedViewpoints } from "@/features/viewpoints/saved-page";

export const metadata: Metadata = { title: "我的观点收藏 · 问与书" };
export default function SavedPage() {
  return <><SiteHeader active="saved" /><main className="reading-page"><div className="page-heading"><p className="eyebrow">把思考，慢慢留下</p><h1>我的观点收藏</h1></div><SavedViewpoints /></main><SiteFooter /></>;
}
