import { FeatureCard } from "@/components/ui/feature-card";
import { SessionStatus } from "@/features/session/status";
import Link from "next/link";

export default function Home() {
  return <main>
    <header><Link href="/" className="brand">问与书<span>WEN YU SHU</span></Link><span className="edition">初见 · 开发预览</span></header>
    <section className="hero"><p className="eyebrow">好奇心，是阅读的开始</p>
      <h1>从一个问题，<br />走向一本好书。</h1>
      <p className="intro">你有因为一个问题而打开一本书吗<br />你有因为一段故事而打开一本书吗<br />你是否有一些思考的问题</p>
      <div className="line" />
    </section>
    <section className="features" aria-label="即将开放的功能">
      <FeatureCard index="01" title="每日一问">从生活中的一个问题出发，发现此刻想了解的方向。</FeatureCard>
      <FeatureCard index="02" title="找本好书">从兴趣、学习目标或疑问出发，遇见值得阅读的作品。</FeatureCard>
      <FeatureCard index="03" title="思辨空间">慢慢说，继续想。在不同视角中，形成自己的理解。</FeatureCard>
    </section>
    <footer><span>信息时代一方阅读与思考的净土</span><SessionStatus /></footer>
  </main>;
}
