"use client";

import { motion } from "framer-motion";

const stats = [
  { value: "10,000+", label: "Сообщений отправлено" },
  { value: "12%", label: "Средняя конверсия в ответ" },
  { value: "3.5x", label: "Рост тёплых лидов" },
  { value: "24/7", label: "Работает без остановки" },
];

export function StatsBar() {
  return (
    <section className="py-16 px-6 border-y border-sg-border bg-sg-surface/30">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              className="text-center"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
            >
              <p className="font-mono text-3xl sm:text-4xl font-bold text-emerald-DEFAULT mb-2">
                {stat.value}
              </p>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
