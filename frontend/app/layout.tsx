import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/nav/Sidebar";
import { Toaster } from "@/components/ui/sonner";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TikTok Live AI Bot",
  description: "Dashboard for TikTok Live AI Bot",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 overflow-auto p-6">{children}</main>
        </div>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
