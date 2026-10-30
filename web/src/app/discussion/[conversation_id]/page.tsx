import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";
import { DiscussionPanel } from "@/features/discussion/panel";
import { notFound } from "next/navigation";

export default async function ExistingDiscussion({ params, searchParams }: { params: Promise<{ conversation_id: string }>; searchParams: Promise<{ message_id?: string }> }) {
  const { conversation_id } = await params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(conversation_id)) notFound();
  const { message_id } = await searchParams;
  return <><SiteHeader active="discussion" /><main className="reading-page"><div className="page-heading"><p className="eyebrow">沿着原来的思考，继续聊</p><h1>回到这段讨论。</h1></div><DiscussionPanel conversationId={conversation_id} sourceMessageId={message_id} /></main><SiteFooter /></>;
}
