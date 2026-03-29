"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const questions = [
  {
    q: "Не заблокируют ли Telegram-аккаунт за рассылку?",
    a: "Signal Grid использует продвинутые механизмы защиты: автоматическая ротация аккаунтов, лимит 30 сообщений в день на аккаунт, человекоподобные задержки между сообщениями, рассылка только в рабочие часы. Всё это минимизирует риск блокировки.",
  },
  {
    q: "Какие источники данных для поиска контактов?",
    a: "Автоматический скраппинг из карт и бизнес-каталогов. Дополнительно — обогащение данными: ИНН, директор, юридическая форма. Вы также можете загрузить собственную базу в формате Excel/CSV.",
  },
  {
    q: "Насколько «умный» AI-бот?",
    a: "Бот ведёт естественные диалоги, обрабатывает возражения, распознаёт голосовые сообщения, извлекает контакты рефералов и адаптирует стиль общения под каждого собеседника.",
  },
  {
    q: "Можно ли настроить тон и стиль сообщений?",
    a: "Да. Вы задаёте системный промпт, оффер и описание услуги. AI использует эти данные для генерации уникальных сообщений. Каждый диалог уникален — никаких шаблонных ответов.",
  },
  {
    q: "Как быстро я увижу первые результаты?",
    a: "Первые ответы обычно приходят в течение первых часов рассылки. Конверсия в ответ — 8–15% в зависимости от ниши и оффера. Тёплые лиды появляются на дашборде в реальном времени.",
  },
  {
    q: "Что происходит с тёплыми лидами?",
    a: "Когда AI определяет, что лид заинтересован, он получает статус «warm» и менеджер получает уведомление в Telegram-бот. Вы можете просматривать все диалоги в веб-интерфейсе и подключаться к разговору в любой момент.",
  },
];

export function FAQ() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section className="py-24 px-6">
      <div className="max-w-3xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
        >
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4 gradient-text">
            Частые вопросы
          </h2>
          <p className="text-muted-foreground">
            Всё, что нужно знать перед стартом
          </p>
        </motion.div>

        <div className="space-y-3">
          {questions.map((item, i) => {
            const isOpen = open === i;
            return (
              <motion.div
                key={i}
                className="rounded-xl border border-sg-border bg-sg-surface overflow-hidden"
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05, duration: 0.3 }}
              >
                <button
                  onClick={() => setOpen(isOpen ? null : i)}
                  className="w-full flex items-center justify-between px-6 py-4 text-left transition-colors hover:bg-sg-hover"
                >
                  <span className="text-sm font-medium text-foreground pr-4">
                    {item.q}
                  </span>
                  <ChevronDown
                    size={18}
                    className={cn(
                      "text-muted-foreground shrink-0 transition-transform duration-200",
                      isOpen && "rotate-180"
                    )}
                  />
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <p className="px-6 pb-4 text-sm text-muted-foreground leading-relaxed">
                        {item.a}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
