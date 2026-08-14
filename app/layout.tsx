import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

const title = "SignalFit｜AI 岗位能力地图";
const description = "专注 AI 产品、AI 全栈 / Agent 工程与 FDE：Coding Agent 本地分析简历，能力基线定期更新，社区可提交 JD、面经与新能力。";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const imageUrl = `${protocol}://${host}/og.png`;

  return {
    title,
    description,
    openGraph: { title, description, type: "website", images: [{ url: imageUrl, width: 1729, height: 910, alt: "SignalFit — Evidence, not vibes." }] },
    twitter: { card: "summary_large_image", title, description, images: [imageUrl] },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
