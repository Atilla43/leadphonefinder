"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowRight, Zap } from "lucide-react";

export function CtaSection() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-3xl mx-auto">
        <motion.div
          className="relative rounded-2xl border border-emerald-500/20 bg-sg-surface p-12 text-center overflow-hidden"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          {/* Glow effect */}
          <div className="absolute inset-0 bg-gradient-to-b from-emerald-500/5 to-transparent pointer-events-none" />
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-48 bg-emerald-500/10 blur-[100px] rounded-full pointer-events-none" />

          <div className="relative">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-emerald-500/20 bg-emerald-500/5 mb-6">
              <Zap size={12} className="text-emerald-DEFAULT" />
              <span className="text-xs text-emerald-DEFAULT font-medium">
                Бесплатный старт
              </span>
            </div>

            <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4 gradient-text">
              Готовы автоматизировать продажи?
            </h2>

            <p className="text-muted-foreground max-w-md mx-auto mb-8">
              Начните с бесплатного тарифа. Настройка занимает 10 минут.
              Первые ответы — в течение часа.
            </p>

            <div className="flex items-center justify-center gap-4">
              <Button size="lg" asChild>
                <Link href="/login">
                  Попробовать бесплатно
                  <ArrowRight size={16} />
                </Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <a href="https://t.me/" target="_blank" rel="noopener noreferrer">
                  Написать в Telegram
                </a>
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
