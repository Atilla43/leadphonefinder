"use client";

import { motion } from "framer-motion";
import { Upload, Cpu, TrendingUp } from "lucide-react";

const steps = [
  {
    number: "01",
    icon: Upload,
    title: "Загрузите базу",
    description:
      "Скраппер автоматически соберёт контакты из карт и бизнес-каталогов. Или загрузите свой Excel-файл.",
  },
  {
    number: "02",
    icon: Cpu,
    title: "Настройте AI",
    description:
      "Задайте оффер, тон общения и расписание. AI адаптируется под каждого собеседника.",
  },
  {
    number: "03",
    icon: TrendingUp,
    title: "Получайте лидов",
    description:
      "Бот рассылает, ведёт диалоги, пингует. Тёплые лиды приходят прямо в дашборд.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4 gradient-text">
            Как это работает
          </h2>
          <p className="text-muted-foreground">
            Три шага от идеи до первых продаж
          </p>
        </motion.div>

        <div className="relative">
          {/* Connecting line */}
          <div className="hidden md:block absolute top-16 left-[16.66%] right-[16.66%] h-px bg-gradient-to-r from-sg-border via-emerald-500/30 to-sg-border" />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-12">
            {steps.map((step, i) => (
              <motion.div
                key={step.number}
                className="text-center relative"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15, duration: 0.4 }}
              >
                {/* Step number */}
                <div className="relative inline-flex items-center justify-center mb-6">
                  <div className="h-14 w-14 rounded-full border border-sg-border bg-sg-surface flex items-center justify-center relative z-10">
                    <step.icon size={22} className="text-emerald-DEFAULT" />
                  </div>
                  <span className="absolute -top-2 -right-2 font-mono text-[10px] font-bold text-emerald-DEFAULT bg-sg-base px-1.5 py-0.5 rounded border border-sg-border">
                    {step.number}
                  </span>
                </div>

                <h3 className="font-semibold text-foreground mb-2 text-lg">
                  {step.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {step.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
