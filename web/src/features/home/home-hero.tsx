import Image from "next/image";
import Link from "next/link";
import { ArrowIcon } from "@/components/ui/line-icon";

export function FeaturedQuestion() {
  return <Link className="featured-question" href="/daily-question" aria-label="进入每日一问：爱，是否应该拥有选择的自由？">
    <div className="featured-image"><Image src="/images/love-at-the-window.webp" alt="雨滴映着城市暮色，两只手在温暖光线中轻轻靠近" fill priority sizes="(max-width: 760px) 90vw, 48vw" /></div>
    <div className="featured-caption"><div><span className="featured-label">每日一问 / 精选</span><h2>爱，是否应该拥有选择的自由？</h2></div><ArrowIcon /></div>
  </Link>;
}

export function HomeHero() {
  return <section className="home-hero" aria-labelledby="home-title">
    <div className="home-hero-copy"><p className="home-eyebrow">在阅读中，重新发现世界<span aria-hidden="true" /></p>
      <h1 id="home-title">让一个好问题，<br /><span>带你走向下一本书。</span></h1>
      <p className="home-tagline">从问题走向阅读，于书中求索答案，衍生新的思考。</p>
      <div className="hero-actions"><Link className="action-button" href="/daily-question">进入每日一问<ArrowIcon /></Link><Link className="text-action" href="/discover">探索书籍<ArrowIcon /></Link></div>
    </div><FeaturedQuestion />
  </section>;
}
