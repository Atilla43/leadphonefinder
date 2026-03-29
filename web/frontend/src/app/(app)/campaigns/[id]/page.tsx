"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  ArrowLeft,
  Search,
  Play,
  Pause,
  XOctagon,
  Trash2,
  Loader2,
  Clock,
} from "lucide-react";
import {
  useCampaign,
  useRecipients,
  launchCampaign,
  pauseCampaign,
  resumeCampaign,
  cancelCampaign,
  deleteCampaign,
} from "@/hooks/use-campaigns";
import { StatusBadge } from "@/components/ui/status-dot";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  formatNumber,
  formatPercent,
  formatPhoneMasked,
  formatRelativeTime,
} from "@/lib/formatters";

export default function CampaignDetailPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const {
    data: campaign,
    isLoading: campaignLoading,
    mutate: mutateCampaign,
  } = useCampaign(id);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState("");
  const { data: recipientsData, isLoading: recipientsLoading } = useRecipients(
    id,
    {
      status: statusFilter || undefined,
      search: search || undefined,
      limit: 100,
    }
  );

  async function handleAction(action: "launch" | "pause" | "resume" | "cancel" | "delete") {
    if (action === "cancel" && !confirm("Отменить кампанию? Это действие необратимо.")) {
      return;
    }
    if (action === "delete" && !confirm("Удалить кампанию и все данные? Это действие необратимо.")) {
      return;
    }

    setActionLoading(true);
    setActionError("");
    try {
      if (action === "launch") await launchCampaign(id);
      else if (action === "pause") await pauseCampaign(id);
      else if (action === "resume") await resumeCampaign(id);
      else if (action === "delete") await deleteCampaign(id);
      else await cancelCampaign(id);
      if (action === "cancel" || action === "delete") {
        router.push("/campaigns");
        return;
      }
      mutateCampaign();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Ошибка выполнения действия");
    } finally {
      setActionLoading(false);
    }
  }

  if (campaignLoading) {
    return (
      <div className="p-8">
        <div className="h-8 w-48 rounded bg-sg-hover animate-pulse mb-6" />
        <div className="h-64 rounded-xl bg-sg-surface animate-pulse" />
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="p-8">
        <p className="text-muted-foreground">Кампания не найдена</p>
      </div>
    );
  }

  const breakdownEntries = Object.entries(campaign.statuses_breakdown).filter(
    ([, count]) => count > 0
  );

  return (
    <div className="p-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-8"
      >
        <Link
          href="/campaigns"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft size={14} />
          Все кампании
        </Link>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-foreground">
              {campaign.name}
            </h1>
            <StatusBadge status={campaign.status} type="campaign" />
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {campaign.status === "pending" && (
              <Button
                onClick={() => handleAction("launch")}
                disabled={actionLoading}
                className="gap-1.5"
              >
                {actionLoading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Play size={16} />
                )}
                Запустить
              </Button>
            )}
            {(campaign.status === "sending" ||
              campaign.status === "listening") && (
              <Button
                variant="outline"
                onClick={() => handleAction("pause")}
                disabled={actionLoading}
                className="gap-1.5 text-amber-400 border-amber-400/30 hover:bg-amber-400/10"
              >
                {actionLoading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Pause size={16} />
                )}
                Пауза
              </Button>
            )}
            {campaign.status === "paused" && (
              <>
                <Button
                  onClick={() => handleAction("resume")}
                  disabled={actionLoading}
                  className="gap-1.5"
                >
                  {actionLoading ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Play size={16} />
                  )}
                  Возобновить
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleAction("cancel")}
                  disabled={actionLoading}
                  className="gap-1.5 text-rose-400 border-rose-400/30 hover:bg-rose-400/10"
                >
                  <XOctagon size={16} />
                  Отменить
                </Button>
              </>
            )}
            {campaign.status === "cancelled" && (
              <Button
                variant="outline"
                onClick={() => handleAction("delete")}
                disabled={actionLoading}
                className="gap-1.5 text-rose-400 border-rose-400/30 hover:bg-rose-400/10"
              >
                {actionLoading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Trash2 size={16} />
                )}
                Удалить
              </Button>
            )}
          </div>
        </div>
        {actionError && (
          <p className="text-sm text-rose-400 mt-2">{actionError}</p>
        )}
        {campaign.offer && (
          <p className="text-muted-foreground text-sm mt-1">
            {campaign.offer}
          </p>
        )}
        {(campaign.work_hour_start != null || campaign.work_hour_end != null) && (
          <div className="flex items-center gap-1.5 mt-2 text-xs text-muted-foreground">
            <Clock size={12} />
            <span>
              Рабочие часы: {campaign.work_hour_start ?? 10}:00–{campaign.work_hour_end ?? 17}:00 МСК
            </span>
          </div>
        )}
      </motion.div>

      {/* Stats cards */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6"
      >
        {[
          { label: "Всего", value: campaign.recipients_total },
          { label: "Отправлено", value: campaign.sent_count },
          {
            label: "Тёплые",
            value: campaign.warm_count,
            color: "text-amber-400",
          },
          {
            label: "Конверсия",
            value:
              campaign.sent_count > 0
                ? formatPercent((campaign.warm_count / campaign.sent_count) * 100)
                : "—",
            isText: true,
            color: "text-emerald-400",
          },
        ].map((item) => (
          <div
            key={item.label}
            className="rounded-xl border border-sg-border bg-sg-surface p-4"
          >
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p
              className={`text-2xl font-semibold mt-1 ${item.color || "text-foreground"}`}
            >
              {item.isText
                ? item.value
                : formatNumber(item.value as number)}
            </p>
          </div>
        ))}
      </motion.div>

      {/* Status breakdown */}
      {breakdownEntries.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="rounded-xl border border-sg-border bg-sg-surface p-5 mb-6"
        >
          <h3 className="text-sm font-medium text-foreground mb-3">
            Распределение по статусам
          </h3>
          <div className="flex flex-wrap gap-2">
            {breakdownEntries.map(([status, count]) => (
              <button
                key={status}
                onClick={() =>
                  setStatusFilter(statusFilter === status ? "" : status)
                }
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm transition-colors ${
                  statusFilter === status
                    ? "border-emerald-DEFAULT/50 bg-emerald-DEFAULT/10 text-emerald-400"
                    : "border-sg-border bg-sg-hover text-muted-foreground hover:text-foreground"
                }`}
              >
                <StatusBadge status={status} type="recipient" />
                <span className="font-medium">{count}</span>
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Recipients table */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="rounded-xl border border-sg-border bg-sg-surface"
      >
        <div className="p-5 border-b border-sg-border flex items-center justify-between gap-4">
          <h3 className="text-sm font-medium text-foreground">
            Получатели
            {recipientsData && (
              <span className="text-muted-foreground ml-2">
                ({recipientsData.total})
              </span>
            )}
          </h3>
          <div className="relative w-64">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              placeholder="Поиск..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-8 text-sm"
            />
          </div>
        </div>

        {recipientsLoading ? (
          <div className="p-5 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="h-10 rounded bg-sg-hover animate-pulse"
              />
            ))}
          </div>
        ) : !recipientsData?.recipients?.length ? (
          <div className="p-8 text-center text-muted-foreground text-sm">
            Нет получателей
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-sg-border text-xs text-muted-foreground">
                  <th className="text-left px-5 py-3 font-medium">
                    Компания
                  </th>
                  <th className="text-left px-5 py-3 font-medium">
                    Контакт
                  </th>
                  <th className="text-left px-5 py-3 font-medium">
                    Телефон
                  </th>
                  <th className="text-left px-5 py-3 font-medium">Статус</th>
                  <th className="text-right px-5 py-3 font-medium">
                    Сообщений
                  </th>
                  <th className="text-right px-5 py-3 font-medium">
                    Последнее
                  </th>
                </tr>
              </thead>
              <tbody>
                {recipientsData.recipients.map((r) => (
                  <tr
                    key={r.phone}
                    className="border-b border-sg-border last:border-0 hover:bg-sg-hover transition-colors"
                  >
                    <td className="px-5 py-3 text-sm text-foreground">
                      {r.messages_count > 0 ? (
                        <Link
                          href={`/conversations/${id}/${encodeURIComponent(r.phone)}`}
                          className="hover:text-emerald-400 transition-colors"
                        >
                          {r.company_name}
                        </Link>
                      ) : (
                        r.company_name
                      )}
                    </td>
                    <td className="px-5 py-3 text-sm text-muted-foreground">
                      {r.contact_name || "—"}
                    </td>
                    <td className="px-5 py-3 text-sm font-mono text-muted-foreground">
                      {formatPhoneMasked(r.phone)}
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={r.status} type="recipient" />
                    </td>
                    <td className="px-5 py-3 text-right font-medium text-sm text-foreground">
                      {r.messages_count}
                    </td>
                    <td className="px-5 py-3 text-right text-xs text-muted-foreground">
                      {r.last_message_at
                        ? formatRelativeTime(r.last_message_at)
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </div>
  );
}
