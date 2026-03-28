"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import type { CampaignSummary } from "@/lib/types";
import { StatusBadge } from "@/components/ui/status-dot";
import { formatNumber, formatPercent } from "@/lib/formatters";

interface CampaignsTableProps {
  campaigns: CampaignSummary[] | undefined;
  isLoading: boolean;
}

export function CampaignsTable({ campaigns, isLoading }: CampaignsTableProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.4 }}
      className="rounded-xl border border-sg-border bg-sg-surface"
    >
      <div className="p-5 border-b border-sg-border">
        <h3 className="text-sm font-medium text-foreground">Кампании</h3>
      </div>

      {isLoading ? (
        <div className="p-5 space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 rounded bg-sg-hover animate-pulse" />
          ))}
        </div>
      ) : !campaigns?.length ? (
        <div className="p-8 text-center text-muted-foreground text-sm">
          Нет кампаний
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-sg-border text-xs text-muted-foreground">
                <th className="text-left px-5 py-3 font-medium">Название</th>
                <th className="text-left px-5 py-3 font-medium">Статус</th>
                <th className="text-right px-5 py-3 font-medium">
                  Отправлено
                </th>
                <th className="text-right px-5 py-3 font-medium">Тёплые</th>
                <th className="text-right px-5 py-3 font-medium">Отказы</th>
                <th className="text-right px-5 py-3 font-medium">Конверсия</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr
                  key={c.campaign_id}
                  className="border-b border-sg-border last:border-0 hover:bg-sg-hover transition-colors"
                >
                  <td className="px-5 py-3">
                    <Link
                      href={`/campaigns/${c.campaign_id}`}
                      className="text-sm text-foreground hover:text-emerald-400 transition-colors"
                    >
                      {c.name}
                    </Link>
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={c.status} type="campaign" />
                  </td>
                  <td className="px-5 py-3 text-right font-stat text-sm text-foreground">
                    {formatNumber(c.sent_count)}
                  </td>
                  <td className="px-5 py-3 text-right font-stat text-sm text-amber-400">
                    {formatNumber(c.warm_count)}
                  </td>
                  <td className="px-5 py-3 text-right font-stat text-sm text-rose-400">
                    {formatNumber(c.rejected_count)}
                  </td>
                  <td className="px-5 py-3 text-right font-stat text-sm text-emerald-400">
                    {formatPercent(c.response_rate)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </motion.div>
  );
}
