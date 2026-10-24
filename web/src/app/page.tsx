import { FeatureCard } from "@/components/ui/feature-card";
import { SessionStatus } from "@/features/session/status";
import Link from "next/link";

export default function Home() {
  return <main>
    <header><Link href="/" className="brand">问与书<span>WEN YU SHU</span></Link><span className="edition">初见 · 开发预览</span></header>
    <section className="hero"><p className="eyebrow">好奇心，是阅读的开始</p>
      <h1>从一个问题，<br />走向一本好书。</h1>
      <p className="intro">让问题打开思考，让阅读延续探索。<br />一个关于好奇心、不同观点与真实阅读的空间。</p>
      <div className="line" /><p className="note">我们正在准备第一批内容。探索、找书与思辨功能将陆续开放。</p>
    </section>
    <section className="features" aria-label="即将开放的功能">
      <FeatureCard index="01" title="每日一问">从生活中的一个问题出发，发现此刻想了解的方向。</FeatureCard>
      <FeatureCard index="02" title="找本好书">从兴趣、学习目标或疑问出发，遇见值得阅读的作品。</FeatureCard>
      <FeatureCard index="03" title="思辨空间">慢慢说，继续想。在不同视角中，形成自己的理解。</FeatureCard>
    </section>
    <footer><span>问与书 · 面向成年人的阅读与思考空间</span><SessionStatus /></footer>
  </main>;
}
