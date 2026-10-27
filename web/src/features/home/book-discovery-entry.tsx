import Link from "next/link";
import { ArrowIcon, DiscoveryIcon } from "@/components/ui/line-icon";

export const discoveryEntries = [
  { mode: "interest", title: "兴趣找书", description: "从喜欢的事物开始" },
  { mode: "question", title: "问题找书", description: "让疑问找到新的线索" },
  { mode: "learning", title: "目标学习", description: "循着目标，建立自己的阅读路径" },
] as const;

export function BookDiscoveryEntry() {
  return <section className="book-discovery" aria-labelledby="discovery-title">
    <h2 id="discovery-title" className="section-title">从你的好奇心出发<span aria-hidden="true" /></h2>
    <div className="discovery-entries">{discoveryEntries.map((entry) => <Link className="discovery-entry" key={entry.mode} href={`/discover?mode=${entry.mode}`}>
      <span className="discovery-icon"><DiscoveryIcon kind={entry.mode} /></span><div className="discovery-copy"><h3>{entry.title}</h3><span>{entry.description}</span></div><ArrowIcon className="entry-arrow" />
    </Link>)}</div>
  </section>;
}
