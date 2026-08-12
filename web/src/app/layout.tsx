import "./globals.css";
import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: {
    default: "板块强度",
    template: "%s | 板块强度",
  },
  description: "股票板块强度分析平台",
};

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f3f6f8" },
    { media: "(prefers-color-scheme: dark)", color: "#171d24" },
  ],
};

const themeScript = `
  (() => {
    try {
      const stored = localStorage.getItem('sector-theme');
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const resolved = stored === 'dark' || (stored !== 'light' && prefersDark) ? 'dark' : 'light';
      document.documentElement.classList.add(resolved);
    } catch (_) {}
  })();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body
        className={`${GeistSans.variable} ${GeistMono.variable} antialiased`}
      >
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
