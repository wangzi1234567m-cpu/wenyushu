import Link from "next/link";

export function FeatureCard({ index, title, children, href }: {
  index: string; title: string; children: React.ReactNode; href?: string;
}) {
  return <article className="card"><span className="index">{index}</span>
    <h2>{title}</h2><p>{children}</p>{href ? <Link className="soon" href={href}>开始探索</Link> : <span className="soon">准备中</span>}</article>;
}
