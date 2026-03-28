"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  Megaphone,
  Settings,
  LogOut,
} from "lucide-react";
import { removeToken } from "@/lib/auth";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Дашборд", icon: LayoutDashboard },
  { href: "/conversations", label: "Диалоги", icon: MessageSquare },
  { href: "/campaigns", label: "Кампании", icon: Megaphone },
  { href: "/settings", label: "Настройки", icon: Settings },
];

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  function handleLogout() {
    removeToken();
    window.location.href = "/login";
  }

  return (
    <div className="min-h-screen bg-sg-base flex">
      {/* Sidebar */}
      <aside className="w-60 shrink-0 border-r border-sg-border bg-sg-sidebar flex flex-col">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 h-16 border-b border-sg-border">
          <div className="h-8 w-8 rounded-lg bg-emerald-DEFAULT flex items-center justify-center">
            <svg
              viewBox="0 0 16 16"
              fill="none"
              className="h-4 w-4 text-sg-base"
            >
              <path
                d="M8 1L14 5V11L8 15L2 11V5L8 1Z"
                fill="currentColor"
              />
              <path
                d="M8 5L11 7V11L8 13L5 11V7L8 5Z"
                fill="#08090d"
                fillOpacity="0.3"
              />
            </svg>
          </div>
          <span className="font-semibold text-sm text-foreground">
            Signal Grid
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                  active
                    ? "bg-emerald-DEFAULT/10 text-emerald-DEFAULT"
                    : "text-muted-foreground hover:text-foreground hover:bg-sg-hover"
                )}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Logout */}
        <div className="px-3 py-4 border-t border-sg-border">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-sg-hover transition-colors w-full"
          >
            <LogOut size={18} />
            Выйти
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="dot-grid min-h-screen">{children}</div>
      </main>
    </div>
  );
}
