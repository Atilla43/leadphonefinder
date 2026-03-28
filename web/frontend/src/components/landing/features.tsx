"use client";

import { motion } from "framer-motion";
import { Bot, BarChart3, RefreshCw, Target } from "lucide-react";

const features = [
  {
    icon: Bot,
    title: "AI-диалоги",
    description:
      "GPT-4 ведёт естественные разговоры, обрабатывает возражения, извлекает контакты рефералов. Каждый диалог уникален.",
  },
  {
    icon: BarChart3,
    title: "Аналитика в реальном времени",
    description:
      "Воронка продаж, конверсии, динамика по дням. WebSocket-обновления — видите каждый ответ мгновенно.",
  },
  {
    icon: RefreshCw,
    title: "Мульти-аккаунт",
    description:
      "Пул Telegram-аккаунтов с round-robin ротацией. 30 сообщений/день на аккаунт, автоматические задержки.",
  },
  {
    icon: Target,
    title: "Автоматический скраппинг",
    description:
      "Яндекс.Карты + 2ГИС. Парсит компании, находит директоров через DaData, дедуплицирует базу.",
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

export function Features() {
  return (
    <section id="features" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
        >
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4 gradient-text">
            Всё для автоматических продаж
          </h2>
          <p className="text-muted-foreground max-w-lg mx-auto">
            От поиска контактов до закрытия сделки — полный цикл без ручной
            работы
          </p>
        </motion.div>

        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5"
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
        >
          {features.map((feature) => (
            <motion.div
              key={feature.title}
              variants={item}
              className="group glass-card rounded-xl p-6 hover:border-sg-border-hover transition-all duration-300 hover:-translate-y-1"
            >
              <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center mb-4 group-hover:bg-emerald-500/20 transition-colors">
                <feature.icon size={20} className="text-emerald-DEFAULT" />
              </div>
              <h3 className="font-semibold text-foreground mb-2">
                {feature.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
