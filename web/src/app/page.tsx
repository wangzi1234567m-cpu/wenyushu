import { SiteHeader } from "@/components/site/site-header";
import { SiteFooter } from "@/components/site/site-footer";
import { HomeHero } from "@/features/home/home-hero";
import { BookDiscoveryEntry } from "@/features/home/book-discovery-entry";
import { ThinkingAssistantEntry } from "@/features/home/thinking-assistant-entry";
import { LegacyDailyRedirect } from "@/features/home/legacy-daily-redirect";

export default function Home() {
  return <><LegacyDailyRedirect /><SiteHeader active="home" />
    <main className="home-page"><div className="home-container"><HomeHero /><BookDiscoveryEntry /></div><ThinkingAssistantEntry /></main>
    <SiteFooter />
  </>;
}
