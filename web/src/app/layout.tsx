import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "问与书", description: "从一个问题，走向一本好书。" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
