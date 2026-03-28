"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Menu, X } from "lucide-react";

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed top-0 w-full z-50 transition-all duration-300",
        scrolled
          ? "bg-sg-base/80 backdrop-blur-xl border-b border-sg-border"
          : "bg-transparent"
      )}
    >
      <nav className="max-w-6xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5">
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
            <span className="font-semibold text-foreground">Signal Grid</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-8">
            <a
              href="#features"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Возможности
            </a>
            <a
              href="#how-it-works"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Как работает
            </a>
            <a
              href="#pricing"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Тарифы
            </a>
          </div>

          {/* CTA */}
          <div className="hidden md:flex items-center gap-3">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/login">Войти</Link>
            </Button>
            <Button size="sm" asChild>
              <Link href="/login">Начать бесплатно</Link>
            </Button>
          </div>

          {/* Mobile toggle */}
          <button
            className="md:hidden text-foreground"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-sg-base/95 backdrop-blur-xl border-t border-sg-border animate-fade-in">
          <div className="px-6 py-4 flex flex-col gap-3">
            <a
              href="#features"
              className="text-sm text-muted-foreground py-2"
              onClick={() => setMobileOpen(false)}
            >
              Возможности
            </a>
            <a
              href="#how-it-works"
              className="text-sm text-muted-foreground py-2"
              onClick={() => setMobileOpen(false)}
            >
              Как работает
            </a>
            <a
              href="#pricing"
              className="text-sm text-muted-foreground py-2"
              onClick={() => setMobileOpen(false)}
            >
              Тарифы
            </a>
            <div className="pt-3 border-t border-sg-border flex flex-col gap-2">
              <Button variant="outline" size="sm" asChild>
                <Link href="/login">Войти</Link>
              </Button>
              <Button size="sm" asChild>
                <Link href="/login">Начать бесплатно</Link>
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
