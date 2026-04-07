"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BarChart2, BookOpen, History, LogOut, Radio, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { api, AuthSeller } from "@/lib/api";
import { Button } from "@/components/ui/button";

const links = [
  { href: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { href: "/monitor", label: "Live Monitor", icon: Radio },
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/sessions", label: "Sessions", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [seller, setSeller] = useState<AuthSeller | null>(null);

  useEffect(() => {
    api.auth.me()
      .then(setSeller)
      .catch(() => setSeller(null));
  }, []);

  async function handleLogout() {
    try {
      await api.auth.logout();
    } catch {
      // Ignore errors
    }
    router.push("/login");
    router.refresh();
  }

  // Don't render sidebar on login page
  if (pathname === "/login") {
    return null;
  }

  return (
    <aside className="flex h-screen w-56 flex-col border-r bg-slate-50 px-3 py-6 shrink-0">
      <div className="mb-8 px-2">
        <h1 className="text-lg font-bold tracking-tight">TikTok Live Bot</h1>
        {seller && (
          <p className="text-sm text-slate-500 truncate" title={seller.name}>
            {seller.name}
          </p>
        )}
      </div>
      <nav className="flex flex-col gap-1 flex-1">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              pathname.startsWith(href)
                ? "bg-slate-200 text-slate-900"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
      <div className="border-t pt-4">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 text-slate-600 hover:text-slate-900"
          onClick={handleLogout}
        >
          <LogOut className="h-4 w-4" />
          Logout
        </Button>
      </div>
    </aside>
  );
}
