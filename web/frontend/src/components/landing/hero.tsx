"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { DashboardPreview } from "./dashboard-preview";
import { ArrowRight, Zap } from "lucide-react";

export function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-start px-6 pt-28 pb-20">
      {/* Announcement badge */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-sg-border bg-sg-surface/50 backdrop-blur-sm">
          <Zap size={12} className="text-emerald-DEFAULT" />
          <span className="text-xs text-muted-foreground">
            AI-powered Telegram Sales
          </span>
          <ArrowRight size={12} className="text-muted-foreground" />
        </div>
      </motion.div>

      {/* Headline */}
      <motion.h1
        className="text-4xl sm:text-5xl lg:text-6xl font-semibold text-center max-w-3xl leading-tight mb-6 tracking-tight"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        <span className="gradient-text">
          Автоматические продажи
          <br />
          через Telegram
        </span>
      </motion.h1>

      {/* Subheadline */}
      <motion.p
        className="text-base sm:text-lg text-muted-foreground text-center max-w-xl mb-10"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        AI-бот находит ЛПР, ведёт диалоги и продаёт ваши услуги.
        <br className="hidden sm:block" />
        Вы наблюдаете за результатами в реальном времени.
      </motion.p>

      {/* CTAs */}
      <motion.div
        className="flex items-center gap-4 mb-16"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5 }}
      >
        <Button size="lg" asChild>
          <Link href="/login">
            Начать бесплатно
            <ArrowRight size={16} />
          </Link>
        </Button>
        <Button variant="outline" size="lg" asChild>
          <a href="#how-it-works">Как это работает</a>
        </Button>
      </motion.div>

      {/* Animated dashboard preview */}
      <DashboardPreview />

      {/* Floating stat badges */}
      <div className="flex flex-wrap justify-center gap-4 mt-12">
        {[
          { label: "сообщений отправлено", value: "10,000+" },
          { label: "конверсия в ответ", value: "12%" },
          { label: "работает без остановки", value: "24/7" },
        ].map((badge, i) => (
          <motion.div
            key={badge.label}
            className="flex items-center gap-2 px-4 py-2 rounded-full border border-sg-border bg-sg-surface/50"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.5 + i * 0.1 }}
          >
            <span className="font-mono text-sm font-bold text-emerald-DEFAULT">
              {badge.value}
            </span>
            <span className="text-xs text-muted-foreground">
              {badge.label}
            </span>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
