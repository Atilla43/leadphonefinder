"use client";

import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TimelinePoint } from "@/lib/types";

interface TimelineChartProps {
  points: TimelinePoint[] | undefined;
  isLoading: boolean;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-sg-border bg-sg-elevated p-3 shadow-lg">
      <p className="text-xs text-muted-foreground mb-2">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2 text-sm">
          <div
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-stat text-foreground">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

const SERIES = [
  { key: "sent", name: "Отправлено", color: "#22d3ee" },
  { key: "replied", name: "Ответили", color: "#10b981" },
  { key: "warm", name: "Тёплые", color: "#f59e0b" },
  { key: "rejected", name: "Отказ", color: "#f43f5e" },
];

export function TimelineChart({ points, isLoading }: TimelineChartProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
      className="rounded-xl border border-sg-border bg-sg-surface p-5"
    >
      <h3 className="text-sm font-medium text-foreground mb-4">
        Динамика рассылки
      </h3>

      {isLoading ? (
        <div className="h-64 rounded bg-sg-hover animate-pulse" />
      ) : !points?.length ? (
        <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
          Нет данных за выбранный период
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={points}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(30,32,48,0.6)"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              axisLine={false}
              tickLine={false}
              width={30}
            />
            <Tooltip content={<CustomTooltip />} />
            {SERIES.map((s) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
                stroke={s.color}
                fill={s.color}
                fillOpacity={0.08}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      )}
    </motion.div>
  );
}
