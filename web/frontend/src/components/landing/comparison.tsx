"use client";

import { motion } from "framer-motion";
import { Check, X } from "lucide-react";

const rows = [
  { feature: "Поиск контактов ЛПР", manual: "Вручную, часы работы", ai: "Автоматически за минуты" },
  { feature: "Первое сообщение", manual: "Copy-paste шаблон", ai: "Персонализированное AI-сообщение" },
  { feature: "Обработка возражений", manual: "Вы сами, один за другим", ai: "AI ведёт 100+ диалогов параллельно" },
  { feature: "Follow-up", manual: "Забываете отправить", ai: "Автопинг по расписанию" },
  { feature: "Аналитика", manual: "Excel-табличка", ai: "Дашборд в реальном времени" },
  { feature: "Масштабирование", manual: "Линейно: больше людей", ai: "Мгновенно: больше аккаунтов" },
  { feature: "Время на 100 лидов", manual: "~40 часов", ai: "~1 минута настройки" },
];

export function Comparison() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
        >
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4 gradient-text">
            Ручная рассылка vs Signal Grid
          </h2>
          <p className="text-muted-foreground">
            Почему AI-автоматизация выигрывает
          </p>
        </motion.div>

        <motion.div
          className="rounded-xl border border-sg-border bg-sg-surface overflow-hidden"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <table className="w-full">
            <thead>
              <tr className="border-b border-sg-border">
                <th className="text-left px-6 py-4 text-sm font-medium text-muted-foreground">
                  Задача
                </th>
                <th className="text-center px-6 py-4 text-sm font-medium text-rose-400">
                  Вручную
                </th>
                <th className="text-center px-6 py-4 text-sm font-medium text-emerald-DEFAULT">
                  Signal Grid
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <motion.tr
                  key={row.feature}
                  className="border-b border-sg-border last:border-0"
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.15 + i * 0.05, duration: 0.3 }}
                >
                  <td className="px-6 py-4 text-sm text-foreground font-medium">
                    {row.feature}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-center gap-2">
                      <X size={14} className="text-rose-400 shrink-0" />
                      <span className="text-xs text-muted-foreground text-center">
                        {row.manual}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-center gap-2">
                      <Check
                        size={14}
                        className="text-emerald-DEFAULT shrink-0"
                      />
                      <span className="text-xs text-foreground text-center">
                        {row.ai}
                      </span>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      </div>
    </section>
  );
}
