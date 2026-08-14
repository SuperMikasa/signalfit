import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

const title = "SignalFit｜AI 岗位能力地图";
const description = "把公开 JD、真实面经和简历证据转化为可解释的岗位能力地图与缺口雷达。";

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
