"use client";

import { motion } from "framer-motion";
import type { FunnelStage } from "@/lib/types";
import { formatNumber } from "@/lib/formatters";

interface FunnelChartProps {
  stages: FunnelStage[] | undefined;
  isLoading: boolean;
}

const STAGE_COLORS: Record<string, string> = {
  pending: "bg-slate-500",
  sent: "bg-cyan-400",
  talking: "bg-blue-400",
  warm: "bg-amber-400",
  warm_confirmed: "bg-emerald-400",
  rejected: "bg-rose-400",
  no_response: "bg-slate-400",
  referral: "bg-purple-400",
  not_found: "bg-slate-600",
  error: "bg-red-600",
};

export function FunnelChart({ stages, isLoading }: FunnelChartProps) {
  const maxCount = stages?.reduce((m, s) => Math.max(m, s.count), 0) || 1;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.35 }}
      className="rounded-xl border border-sg-border bg-sg-surface p-5"
    >
      <h3 className="text-sm font-medium text-foreground mb-4">
        Воронка конверсии
      </h3>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 rounded bg-sg-hover animate-pulse" />
          ))}
        </div>
      ) : !stages?.length ? (
        <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
          Нет данных
        </div>
      ) : (
        <div className="space-y-3">
          {stages.map((stage, i) => {
            const width = Math.max((stage.count / maxCount) * 100, 4);
            const color = STAGE_COLORS[stage.stage] || "bg-slate-500";

            return (
              <div key={stage.stage}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-muted-foreground">{stage.label}</span>
                  <span className="font-stat text-foreground">
                    {formatNumber(stage.count)}
                  </span>
                </div>
                <div className="h-7 bg-sg-hover rounded-lg overflow-hidden">
                  <motion.div
                    className={`h-full ${color} rounded-lg`}
                    initial={{ width: 0 }}
                    animate={{ width: `${width}%` }}
                    transition={{
                      duration: 0.6,
                      delay: 0.4 + i * 0.06,
                      ease: "easeOut",
                    }}
                    style={{ opacity: 0.7 }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
