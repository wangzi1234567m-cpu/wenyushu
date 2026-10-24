export function FeatureCard({ index, title, children }: {
  index: string; title: string; children: React.ReactNode;
}) {
  return <article className="card"><span className="index">{index}</span>
    <h2>{title}</h2><p>{children}</p><span className="soon">准备中</span></article>;
}
