"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  useAccounts,
  toggleAccount,
  removeAccount,
  type AccountItem,
} from "@/hooks/use-accounts";
import type { HealthStatus } from "@/lib/types";
import useSWR from "swr";
import { fetcher } from "@/lib/api-client";
import {
  Activity,
  Server,
  FolderOpen,
  Users,
  Wifi,
  Phone,
  CheckCircle2,
  XCircle,
  Plus,
  Power,
  Trash2,
  Plug,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { AccountAddDialog } from "@/components/settings/account-add-dialog";
import { AccountOtpDialog } from "@/components/settings/account-otp-dialog";

export default function SettingsPage() {
  const { data: health } = useSWR<HealthStatus>("/api/health", fetcher, {
    refreshInterval: 15_000,
  });
  const { data: accountsData, mutate: mutateAccounts } = useAccounts();

  const [showAddDialog, setShowAddDialog] = useState(false);
  const [connectingPhone, setConnectingPhone] = useState<string | null>(null);
  const [togglingPhone, setTogglingPhone] = useState<string | null>(null);
  const [deletingPhone, setDeletingPhone] = useState<string | null>(null);

  async function handleToggle(phone: string) {
    setTogglingPhone(phone);
    try {
      await toggleAccount(phone);
      mutateAccounts();
    } catch {
      // error handled by apiFetch
    } finally {
      setTogglingPhone(null);
    }
  }

  async function handleDelete(phone: string) {
    if (!confirm(`Удалить аккаунт ${phone}?`)) return;
    setDeletingPhone(phone);
    try {
      await removeAccount(phone);
      mutateAccounts();
    } catch {
      // error handled by apiFetch
    } finally {
      setDeletingPhone(null);
    }
  }

  const accounts = accountsData?.accounts || [];
  const healthLoading = !health;

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
          Статус системы и управление аккаунтами
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

        {healthLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-8 rounded bg-sg-hover animate-pulse" />
            ))}
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
          {accountsData && (
            <span className="text-xs text-muted-foreground ml-auto mr-3">
              {accountsData.connected_accounts} подключено / {accountsData.total_accounts} всего
            </span>
          )}
          <Button
            size="sm"
            onClick={() => setShowAddDialog(true)}
            className="gap-1"
          >
            <Plus size={14} />
            Добавить
          </Button>
        </div>

        {!accountsData ? (
          <div className="space-y-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="h-14 rounded bg-sg-hover animate-pulse" />
            ))}
          </div>
        ) : accounts.length === 0 ? (
          <div className="text-center py-8">
            <Phone size={32} className="mx-auto mb-3 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground mb-4">
              Нет добавленных аккаунтов
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAddDialog(true)}
              className="gap-1"
            >
              <Plus size={14} />
              Добавить аккаунт
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            {accounts.map((acc) => (
              <AccountRow
                key={acc.phone}
                account={acc}
                isToggling={togglingPhone === acc.phone}
                isDeleting={deletingPhone === acc.phone}
                onConnect={() => setConnectingPhone(acc.phone)}
                onToggle={() => handleToggle(acc.phone)}
                onDelete={() => handleDelete(acc.phone)}
              />
            ))}
          </div>
        )}
      </motion.div>

      {/* Dialogs */}
      <AccountAddDialog
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        onSuccess={() => mutateAccounts()}
      />
      {connectingPhone && (
        <AccountOtpDialog
          open={!!connectingPhone}
          onOpenChange={(open) => {
            if (!open) setConnectingPhone(null);
          }}
          phone={connectingPhone}
          onSuccess={() => {
            setConnectingPhone(null);
            mutateAccounts();
          }}
        />
      )}
    </div>
  );
}

function AccountRow({
  account,
  isToggling,
  isDeleting,
  onConnect,
  onToggle,
  onDelete,
}: {
  account: AccountItem;
  isToggling: boolean;
  isDeleting: boolean;
  onConnect: () => void;
  onToggle: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-sg-hover group">
      <Phone size={14} className="text-muted-foreground shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">
            {account.phone_masked}
          </span>
          {account.connected ? (
            <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Подключён
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
              Не подключён
            </span>
          )}
          {!account.active && (
            <span className="text-xs text-amber-400">(выключен)</span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
          <span>{account.session_name}</span>
          {account.connected && (
            <span>
              Отправлено: {account.sent_today}/{account.daily_limit}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
        {!account.connected && (
          <button
            onClick={onConnect}
            className="p-1.5 rounded-md hover:bg-sg-elevated text-emerald-400 transition-colors"
            title="Подключить (OTP)"
          >
            <Plug size={14} />
          </button>
        )}
        <button
          onClick={onToggle}
          disabled={isToggling}
          className={`p-1.5 rounded-md hover:bg-sg-elevated transition-colors ${
            account.active ? "text-amber-400" : "text-emerald-400"
          }`}
          title={account.active ? "Деактивировать" : "Активировать"}
        >
          {isToggling ? <Loader2 size={14} className="animate-spin" /> : <Power size={14} />}
        </button>
        <button
          onClick={onDelete}
          disabled={isDeleting}
          className="p-1.5 rounded-md hover:bg-sg-elevated text-rose-400 transition-colors"
          title="Удалить"
        >
          {isDeleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
        </button>
      </div>
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
          <span className="text-sm font-medium text-foreground">{value}</span>
        ) : ok ? (
          <CheckCircle2 size={16} className="text-emerald-400" />
        ) : (
          <XCircle size={16} className="text-rose-400" />
        )}
      </span>
    </div>
  );
}
