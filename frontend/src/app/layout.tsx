import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Header } from "@/components/Header";
import { ClientLayout } from "@/components/ClientLayout";
import { DisplayCurrencyProvider } from "@/contexts/DisplayCurrencyContext";
import { ColorSchemeProvider } from "@/contexts/ColorSchemeContext";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "PFA — 个人投研助理",
  description: "AI-powered portfolio research assistant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className={`${inter.variable} min-h-screen bg-[#0A0F1E] text-white antialiased`}>
        <DisplayCurrencyProvider>
          <ColorSchemeProvider>
            <Header />
            <main className="pt-12">
              <ClientLayout>{children}</ClientLayout>
            </main>
          </ColorSchemeProvider>
        </DisplayCurrencyProvider>
      </body>
    </html>
  );
}
