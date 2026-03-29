"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  ArrowLeft,
  Upload,
  FileSpreadsheet,
  X,
  Loader2,
  Rocket,
  Save,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { launchCampaign } from "@/hooks/use-campaigns";
import { getToken } from "@/lib/auth";
import { API_URL } from "@/lib/constants";

export default function NewCampaignPage() {
  const router = useRouter();

  // File
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Campaign fields
  const [name, setName] = useState("");
  const [offer, setOffer] = useState("");
  const [serviceInfo, setServiceInfo] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [managerIds, setManagerIds] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // State
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function handleFile(f: File) {
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (!["csv", "xlsx", "xls"].includes(ext || "")) {
      setError("Поддерживаются только файлы .csv, .xlsx, .xls");
      return;
    }
    setFile(f);
    setError("");
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  async function handleSubmit(andLaunch: boolean) {
    if (!offer.trim()) {
      setError("Оффер обязателен");
      return;
    }
    if (!file) {
      setError("Выберите файл с контактами");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const token = getToken();
      const formData = new FormData();
      formData.append("file", file);
      formData.append("offer", offer.trim());
      if (name.trim()) formData.append("name", name.trim());
      if (serviceInfo.trim()) formData.append("service_info", serviceInfo.trim());
      if (systemPrompt.trim()) formData.append("system_prompt", systemPrompt.trim());
      if (managerIds.trim()) formData.append("manager_ids", managerIds.trim());

      const res = await fetch(`${API_URL}/api/campaigns/create`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || "Ошибка создания кампании");
      }

      const data = await res.json();
      const campaignId = data.campaign_id;

      if (andLaunch) {
        try {
          await launchCampaign(campaignId);
        } catch {
          // Campaign created but launch failed — still redirect
        }
      }

      router.push(`/campaigns/${campaignId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка создания кампании");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="p-8 max-w-3xl">
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
        <h1 className="text-2xl font-semibold text-foreground">
          Новая кампания
        </h1>
      </motion.div>

      {/* Step 1: File upload */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="rounded-xl border border-sg-border bg-sg-surface p-5 mb-6"
      >
        <h3 className="text-sm font-medium text-foreground mb-4">
          1. Загрузите файл с контактами
        </h3>

        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
            e.target.value = "";
          }}
        />
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            dragOver
              ? "border-emerald-DEFAULT/50 bg-emerald-DEFAULT/5"
              : file
                ? "border-emerald-DEFAULT/30 bg-emerald-DEFAULT/5"
                : "border-sg-border hover:border-emerald-DEFAULT/30"
          }`}
        >
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileSpreadsheet size={24} className="text-emerald-400" />
              <div className="text-left">
                <p className="text-sm text-foreground">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                className="p-1 hover:bg-sg-hover rounded transition-colors text-muted-foreground hover:text-foreground"
              >
                <X size={16} />
              </button>
            </div>
          ) : (
            <>
              <Upload size={32} className="mx-auto mb-3 text-muted-foreground" />
              <p className="text-sm text-foreground">Перетащите файл сюда</p>
              <p className="text-xs text-muted-foreground mt-1">
                .csv, .xlsx — с колонками: phone, company_name
              </p>
            </>
          )}
        </div>
      </motion.div>

      {/* Step 2: Offer */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.15 }}
        className="rounded-xl border border-sg-border bg-sg-surface p-5 mb-6"
      >
        <h3 className="text-sm font-medium text-foreground mb-4">
          2. Оффер
        </h3>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="new-offer">
              Предложение для лидов *
            </Label>
            <Textarea
              id="new-offer"
              value={offer}
              onChange={(e) => setOffer(e.target.value)}
              placeholder="Предложение, которое будет отправлено вместе с первым сообщением..."
              className="min-h-[100px]"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-name">
              Название кампании
            </Label>
            <Input
              id="new-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Авто-заполнится из оффера"
            />
          </div>
        </div>

        {/* Advanced settings */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-1.5 mt-4 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {showAdvanced ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          Дополнительные настройки
        </button>

        {showAdvanced && (
          <div className="space-y-4 mt-4 pt-4 border-t border-sg-border">
            <div className="space-y-2">
              <Label htmlFor="new-service-info">Информация об услуге</Label>
              <Textarea
                id="new-service-info"
                value={serviceInfo}
                onChange={(e) => setServiceInfo(e.target.value)}
                placeholder="Детали услуги для AI-продажника (цены, условия, кейсы)..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-prompt">Системный промпт</Label>
              <Textarea
                id="new-prompt"
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="Кастомный промпт для AI (опционально)..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-manager-ids">Telegram ID менеджеров</Label>
              <Input
                id="new-manager-ids"
                value={managerIds}
                onChange={(e) => setManagerIds(e.target.value)}
                placeholder="ID через запятую: 123456789, 987654321"
              />
              <p className="text-xs text-muted-foreground">
                Менеджеры получат уведомления о тёплых лидах в Telegram
              </p>
            </div>
          </div>
        )}
      </motion.div>

      {/* Error */}
      {error && (
        <p className="text-sm text-rose-400 mb-4">{error}</p>
      )}

      {/* Actions */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="flex items-center justify-end gap-3"
      >
        <Button
          variant="outline"
          onClick={() => handleSubmit(false)}
          disabled={saving || !offer.trim() || !file}
          className="gap-1.5"
        >
          {saving ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Save size={16} />
          )}
          Создать
        </Button>
        <Button
          onClick={() => handleSubmit(true)}
          disabled={saving || !offer.trim() || !file}
          className="gap-1.5"
        >
          {saving ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Rocket size={16} />
          )}
          Создать и запустить
        </Button>
      </motion.div>
    </div>
  );
}
