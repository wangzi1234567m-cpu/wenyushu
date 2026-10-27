import Link from "next/link";
import { ArrowIcon } from "@/components/ui/line-icon";

export function ThinkingAssistantEntry() {
  return <section className="thinking-entry" aria-labelledby="thinking-title"><div className="home-container thinking-inner">
    <div><h2 id="thinking-title">有些问题，值得慢慢聊。</h2><p>思辨助手陪你梳理观点，也陪你找到值得读的书。</p></div>
    <Link className="action-button" href="/discussion">开启思辨<ArrowIcon /></Link>
  </div></section>;
}
