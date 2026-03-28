"use client";

import { motion, useSpring, useTransform } from "framer-motion";
import { useEffect } from "react";

function AnimatedNumber({ target, delay = 0 }: { target: number; delay?: number }) {
  const spring = useSpring(0, { damping: 80, stiffness: 60 });
  const display = useTransform(spring, (v) =>
    Math.round(v).toLocaleString("ru-RU")
  );

  useEffect(() => {
    const timeout = setTimeout(() => spring.set(target), delay);
    return () => clearTimeout(timeout);
  }, [spring, target, delay]);

  return <motion.span>{display}</motion.span>;
}

function MiniChart() {
  const bars = [35, 48, 42, 65, 55, 72, 60, 85, 78, 92, 88, 95];
  return (
    <div className="flex items-end gap-[3px] h-10">
      {bars.map((h, i) => (
        <motion.div
          key={i}
          className="w-[6px] rounded-sm bg-emerald-500/60"
          initial={{ height: 0 }}
          animate={{ height: `${h}%` }}
          transition={{ delay: 0.8 + i * 0.05, duration: 0.4, ease: "easeOut" }}
        />
      ))}
    </div>
  );
}

export function DashboardPreview() {
  return (
    <motion.div
      className="relative w-full max-w-3xl mx-auto"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.6 }}
    >
      {/* Browser frame */}
      <div className="rounded-xl border border-sg-border bg-sg-surface overflow-hidden shadow-2xl shadow-black/40">
        {/* Title bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-sg-border bg-sg-sidebar">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-rose-500/60" />
            <div className="w-3 h-3 rounded-full bg-amber-500/60" />
            <div className="w-3 h-3 rounded-full bg-emerald-500/60" />
          </div>
          <div className="flex-1 text-center">
            <span className="text-[11px] text-muted-foreground font-mono">
              app.signalgrid.ru/dashboard
            </span>
          </div>
        </div>

        {/* Dashboard content */}
        <div className="p-5 dot-grid">
          {/* KPI row */}
          <div className="grid grid-cols-4 gap-3 mb-4">
            {[
              { label: "Отправлено", value: 1247, color: "text-foreground" },
              { label: "Ответили", value: 312, color: "text-cyan-400" },
              { label: "Warm", value: 89, color: "text-emerald-400" },
              { label: "Конверсия", value: 7.1, color: "text-emerald-400", suffix: "%" },
            ].map((stat, i) => (
              <div
                key={stat.label}
                className="rounded-lg border border-sg-border bg-sg-base/50 p-3"
              >
                <div className="text-[10px] text-muted-foreground mb-1">
                  {stat.label}
                </div>
                <div className={`font-mono text-lg font-bold ${stat.color}`}>
                  <AnimatedNumber target={stat.value} delay={400 + i * 150} />
                  {stat.suffix || ""}
                </div>
              </div>
            ))}
          </div>

          {/* Chart area */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2 rounded-lg border border-sg-border bg-sg-base/50 p-3">
              <div className="text-[10px] text-muted-foreground mb-2">
                Динамика за 30 дней
              </div>
              <MiniChart />
            </div>
            <div className="rounded-lg border border-sg-border bg-sg-base/50 p-3">
              <div className="text-[10px] text-muted-foreground mb-2">
                Воронка
              </div>
              <div className="space-y-1.5">
                {[
                  { label: "Sent", w: "100%", color: "bg-amber-500/40" },
                  { label: "Talk", w: "65%", color: "bg-cyan-500/40" },
                  { label: "Warm", w: "28%", color: "bg-emerald-500/50" },
                  { label: "Deal", w: "12%", color: "bg-emerald-500" },
                ].map((item, i) => (
                  <div key={item.label} className="flex items-center gap-2">
                    <span className="text-[9px] text-muted-foreground w-6">
                      {item.label}
                    </span>
                    <div className="flex-1 h-2 rounded-full bg-sg-hover overflow-hidden">
                      <motion.div
                        className={`h-full rounded-full ${item.color}`}
                        initial={{ width: 0 }}
                        animate={{ width: item.w }}
                        transition={{
                          delay: 1.2 + i * 0.15,
                          duration: 0.6,
                          ease: "easeOut",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Glow effect behind */}
      <div className="absolute -inset-10 -z-10 bg-emerald-500/5 rounded-3xl blur-3xl" />
    </motion.div>
  );
}
