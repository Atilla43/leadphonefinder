"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";

const plans = [
  {
    name: "Starter",
    price: "Бесплатно",
    period: "",
    description: "Для знакомства с платформой",
    features: [
      "100 сообщений/мес",
      "1 Telegram-аккаунт",
      "Базовая аналитика",
      "AI-диалоги (базовая модель)",
    ],
    cta: "Начать бесплатно",
    featured: false,
  },
  {
    name: "Pro",
    price: "4,990",
    period: "₽/мес",
    description: "Для активных продаж",
    features: [
      "1,000 сообщений/мес",
      "3 Telegram-аккаунта",
      "Полная аналитика + воронка",
      "AI-диалоги (продвинутая модель)",
      "Автоматический скраппинг",
      "Приоритетная поддержка",
    ],
    cta: "Выбрать Pro",
    featured: true,
  },
  {
    name: "Enterprise",
    price: "14,990",
    period: "₽/мес",
    description: "Для команд и агентств",
    features: [
      "Безлимит сообщений",
      "10 Telegram-аккаунтов",
      "API доступ",
      "Мульти-пользователи",
      "Кастомные AI-промпты",
      "Персональный менеджер",
      "SLA 99.9%",
    ],
    cta: "Связаться",
    featured: false,
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4 gradient-text">
            Простые тарифы
          </h2>
          <p className="text-muted-foreground">
            Начните бесплатно, масштабируйтесь когда готовы
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan, i) => (
            <motion.div
              key={plan.name}
              className={cn(
                "relative rounded-xl border p-6 flex flex-col transition-all duration-300 hover:-translate-y-1",
                plan.featured
                  ? "border-emerald-500/40 bg-sg-surface glow-emerald"
                  : "border-sg-border bg-sg-surface hover:border-sg-border-hover"
              )}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
            >
              {plan.featured && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                  <span className="bg-emerald-500/15 text-emerald-DEFAULT text-[20px] font-bold px-5 py-1.5 rounded-xl border border-emerald-500/30">
                    Популярный
                  </span>
                </div>
              )}

              <div className="mb-6">
                <h3 className="font-semibold text-foreground text-lg mb-1">
                  {plan.name}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {plan.description}
                </p>
              </div>

              <div className="mb-6">
                <span className="font-mono text-4xl font-bold text-foreground">
                  {plan.price}
                </span>
                {plan.period && (
                  <span className="text-muted-foreground ml-1">
                    {plan.period}
                  </span>
                )}
              </div>

              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <Check
                      size={16}
                      className="text-emerald-DEFAULT mt-0.5 shrink-0"
                    />
                    {feature}
                  </li>
                ))}
              </ul>

              <Button
                variant={plan.featured ? "default" : "outline"}
                className="w-full"
                asChild
              >
                <Link href="/login">{plan.cta}</Link>
              </Button>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
