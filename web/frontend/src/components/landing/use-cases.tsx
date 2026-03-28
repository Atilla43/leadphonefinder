"use client";

import { motion } from "framer-motion";
import {
  Building,
  Briefcase,
  GraduationCap,
  Rocket,
} from "lucide-react";

const cases = [
  {
    icon: Building,
    title: "Агентства и студии",
    description:
      "Автоматизируйте поиск клиентов для вашего digital-агентства. Бот найдёт компании без сайта, без рекламы — и предложит ваши услуги.",
    tag: "B2B продажи",
  },
  {
    icon: Briefcase,
    title: "Фрилансеры",
    description:
      "Перестаньте тратить часы на холодные рассылки. AI ведёт десятки диалогов параллельно — вы подключаетесь только к тёплым лидам.",
    tag: "Масштабирование",
  },
  {
    icon: GraduationCap,
    title: "Образовательные проекты",
    description:
      "Находите директоров школ, курсов и центров через 2ГИС. Бот расскажет о вашем продукте естественным языком.",
    tag: "EdTech",
  },
  {
    icon: Rocket,
    title: "Стартапы",
    description:
      "Тестируйте product-market fit быстрее. Отправьте оффер сотням ЛПР за день и получите реальную обратную связь от рынка.",
    tag: "Growth",
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

export function UseCases() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
        >
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight mb-4 gradient-text">
            Для кого Signal Grid
          </h2>
          <p className="text-muted-foreground max-w-lg mx-auto">
            Любой бизнес, которому нужны клиенты из Telegram
          </p>
        </motion.div>

        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 gap-5"
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
        >
          {cases.map((c) => (
            <motion.div
              key={c.title}
              variants={item}
              className="group glass-card rounded-xl p-6 hover:border-sg-border-hover transition-all duration-300"
            >
              <div className="flex items-start gap-4">
                <div className="h-12 w-12 rounded-xl bg-emerald-500/10 flex items-center justify-center shrink-0 group-hover:bg-emerald-500/20 transition-colors">
                  <c.icon size={24} className="text-emerald-DEFAULT" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold text-foreground">
                      {c.title}
                    </h3>
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-DEFAULT/10 text-emerald-DEFAULT">
                      {c.tag}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {c.description}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
