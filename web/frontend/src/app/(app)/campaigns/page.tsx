"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useCampaigns } from "@/hooks/use-campaigns";
import { StatusBadge } from "@/components/ui/status-dot";
import { formatNumber, formatPercent } from "@/lib/formatters";
import { Send, Flame, XCircle, Users } from "lucide-react";

export default function CampaignsPage() {
  const { data, isLoading } = useCampaigns();

  return (
    <div className="p-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-8"
      >
        <h1 className="text-2xl font-semibold text-foreground mb-1">
          Кампании
        </h1>
        <p className="text-muted-foreground text-sm">
          Управление рассылочными кампаниями
        </p>
      </motion.div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-48 rounded-xl border border-sg-border bg-sg-surface animate-pulse"
            />
          ))}
        </div>
      ) : !data?.campaigns?.length ? (
        <div className="rounded-xl border border-sg-border bg-sg-surface p-12 text-center">
          <p className="text-muted-foreground">Нет кампаний</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {data.campaigns.map((c, i) => (
            <motion.div
              key={c.campaign_id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 + i * 0.05 }}
            >
              <Link
                href={`/campaigns/${c.campaign_id}`}
                className="block rounded-xl border border-sg-border bg-sg-surface p-5 hover:border-emerald-DEFAULT/30 transition-colors group"
              >
                <div className="flex items-start justify-between mb-4">
                  <h3 className="text-sm font-medium text-foreground group-hover:text-emerald-400 transition-colors truncate mr-3">
                    {c.name}
                  </h3>
                  <StatusBadge status={c.status} type="campaign" />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="flex items-center gap-2">
                    <Users size={14} className="text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">
                      Всего
                    </span>
                    <span className="text-sm font-stat text-foreground ml-auto">
                      {formatNumber(c.recipients_total)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Send size={14} className="text-cyan-400" />
                    <span className="text-xs text-muted-foreground">
                      Отправлено
                    </span>
                    <span className="text-sm font-stat text-foreground ml-auto">
                      {formatNumber(c.sent_count)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Flame size={14} className="text-amber-400" />
                    <span className="text-xs text-muted-foreground">
                      Тёплые
                    </span>
                    <span className="text-sm font-stat text-amber-400 ml-auto">
                      {formatNumber(c.warm_count)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <XCircle size={14} className="text-rose-400" />
                    <span className="text-xs text-muted-foreground">
                      Отказы
                    </span>
                    <span className="text-sm font-stat text-rose-400 ml-auto">
                      {formatNumber(c.rejected_count)}
                    </span>
                  </div>
                </div>

                {c.sent_count > 0 && (
                  <div className="mt-4 pt-3 border-t border-sg-border flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      Конверсия ответа
                    </span>
                    <span className="text-sm font-stat text-emerald-400">
                      {formatPercent(c.response_rate)}
                    </span>
                  </div>
                )}
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
