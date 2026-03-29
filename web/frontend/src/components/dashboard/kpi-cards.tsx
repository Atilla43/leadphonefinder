"use client";

import { motion } from "framer-motion";
import { Send, MessageSquare, Flame, TrendingUp } from "lucide-react";
import type { DashboardStats } from "@/lib/types";
import { formatNumber, formatPercent } from "@/lib/formatters";

interface KpiCardsProps {
  stats: DashboardStats | undefined;
  isLoading: boolean;
}

const cards = [
  {
    key: "total_sent" as const,
    label: "Отправлено",
    icon: Send,
    color: "text-cyan-400",
    bg: "bg-cyan-400/10",
    format: formatNumber,
  },
  {
    key: "total_replied" as const,
    label: "Ответили",
    icon: MessageSquare,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
    format: formatNumber,
  },
  {
    key: "total_warm" as const,
    label: "Тёплые",
    icon: Flame,
    color: "text-amber-400",
    bg: "bg-amber-400/10",
    format: formatNumber,
  },
  {
    key: "conversion_rate" as const,
    label: "Конверсия",
    icon: TrendingUp,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
    format: formatPercent,
  },
];

export function KpiCards({ stats, isLoading }: KpiCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, i) => (
        <motion.div
          key={card.key}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 + i * 0.05 }}
          className="rounded-xl border border-sg-border bg-sg-surface p-5"
        >
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">{card.label}</p>
            <div className={`${card.bg} ${card.color} p-2 rounded-lg`}>
              <card.icon size={16} />
            </div>
          </div>
          {isLoading ? (
            <div className="h-9 w-20 rounded bg-sg-hover animate-pulse" />
          ) : (
            <p className="text-3xl font-semibold font-stat text-foreground">
              {stats ? card.format(stats[card.key]) : "—"}
            </p>
          )}
        </motion.div>
      ))}
    </div>
  );
}
