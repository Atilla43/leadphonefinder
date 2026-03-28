"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { apiFetch } from "@/lib/api-client";
import type { HealthStatus, AccountsResponse } from "@/lib/types";
import {
  Activity,
  Server,
  FolderOpen,
  Users,
  Wifi,
  Phone,
  CheckCircle2,
  XCircle,
} from "lucide-react";

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [accounts, setAccounts] = useState<AccountsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch<HealthStatus>("/api/health").catch(() => null),
      apiFetch<AccountsResponse>("/api/accounts").catch(() => null),
    ]).then(([h, a]) => {
      setHealth(h);
      setAccounts(a);
      setLoading(false);
    });
  }, []);

  return (
    <div className="p-8 max-w-3xl">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-8"
      >
        <h1 className="text-2xl font-semibold text-foreground mb-1">
          Настройки
        </h1>
        <p className="text-muted-foreground text-sm">
          Статус системы и подключённые аккаунты
        </p>
      </motion.div>

      {/* System health */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="rounded-xl border border-sg-border bg-sg-surface p-5 mb-6"
      >
        <div className="flex items-center gap-2 mb-4">
          <Activity size={16} className="text-emerald-400" />
          <h3 className="text-sm font-medium text-foreground">
            Статус системы
          </h3>
        </div>

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-8 rounded bg-sg-hover animate-pulse" />
            ))}
          </div>
        ) : !health ? (
          <div className="flex items-center gap-2 text-rose-400 text-sm">
            <XCircle size={16} />
            API недоступен
          </div>
        ) : (
          <div className="space-y-3">
            <StatusRow
              icon={<Server size={14} />}
              label="API сервер"
              ok={health.status === "ok"}
            />
            <StatusRow
              icon={<FolderOpen size={14} />}
              label="Директория кампаний"
              ok={health.outreach_dir_exists}
            />
            <StatusRow
              icon={<FolderOpen size={14} />}
              label="Директория кеша"
              ok={health.cache_dir_exists}
            />
            <StatusRow
              icon={<Wifi size={14} />}
              label="WebSocket подключений"
              value={String(health.ws_connections)}
            />
          </div>
        )}
      </motion.div>

      {/* Accounts */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="rounded-xl border border-sg-border bg-sg-surface p-5"
      >
        <div className="flex items-center gap-2 mb-4">
          <Users size={16} className="text-cyan-400" />
          <h3 className="text-sm font-medium text-foreground">
            Telethon аккаунты
          </h3>
          {accounts && (
            <span className="text-xs text-muted-foreground ml-auto">
              {accounts.active_accounts} / {accounts.total_accounts} активных
            </span>
          )}
        </div>

        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="h-12 rounded bg-sg-hover animate-pulse" />
            ))}
          </div>
        ) : !accounts?.accounts.length ? (
          <p className="text-muted-foreground text-sm">
            Нет подключённых аккаунтов
          </p>
        ) : (
          <div className="space-y-2">
            {accounts.accounts.map((acc) => (
              <div
                key={acc.session_name}
                className="flex items-center gap-3 px-4 py-3 rounded-lg bg-sg-hover"
              >
                <Phone size={14} className="text-muted-foreground" />
                <span className="text-sm font-stat text-foreground">
                  {acc.phone_masked}
                </span>
                <span className="text-xs text-muted-foreground">
                  {acc.session_name}
                </span>
                <span className="ml-auto">
                  {acc.active ? (
                    <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      Активен
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                      <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
                      Неактивен
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}

function StatusRow({
  icon,
  label,
  ok,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  ok?: boolean;
  value?: string;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-sg-hover">
      <span className="text-muted-foreground">{icon}</span>
      <span className="text-sm text-foreground">{label}</span>
      <span className="ml-auto">
        {value !== undefined ? (
          <span className="text-sm font-stat text-foreground">{value}</span>
        ) : ok ? (
          <CheckCircle2 size={16} className="text-emerald-400" />
        ) : (
          <XCircle size={16} className="text-rose-400" />
        )}
      </span>
    </div>
  );
}
