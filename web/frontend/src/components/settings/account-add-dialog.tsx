"use client";

import { useState } from "react";
import { Loader2, Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { addAccount } from "@/hooks/use-accounts";

interface AccountAddDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function AccountAddDialog({
  open,
  onOpenChange,
  onSuccess,
}: AccountAddDialogProps) {
  const [phone, setPhone] = useState("");
  const [apiId, setApiId] = useState("");
  const [apiHash, setApiHash] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function handleOpenChange(isOpen: boolean) {
    if (!isOpen) {
      setPhone("");
      setApiId("");
      setApiHash("");
      setError("");
    }
    onOpenChange(isOpen);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!phone.trim() || !apiId.trim() || !apiHash.trim()) {
      setError("Все поля обязательны");
      return;
    }

    const parsedApiId = parseInt(apiId, 10);
    if (isNaN(parsedApiId)) {
      setError("API ID должен быть числом");
      return;
    }

    setSaving(true);
    setError("");

    try {
      await addAccount(phone.trim(), parsedApiId, apiHash.trim());
      handleOpenChange(false);
      onSuccess();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Ошибка добавления аккаунта"
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus size={18} className="text-emerald-400" />
            Добавить аккаунт
          </DialogTitle>
          <DialogDescription>
            Получите API ID и API Hash на{" "}
            <a
              href="https://my.telegram.org"
              target="_blank"
              rel="noopener noreferrer"
              className="text-emerald-400 underline"
            >
              my.telegram.org
            </a>
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="acc-phone">Номер телефона</Label>
              <Input
                id="acc-phone"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+79001234567"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="acc-api-id">API ID</Label>
              <Input
                id="acc-api-id"
                value={apiId}
                onChange={(e) => setApiId(e.target.value)}
                placeholder="12345678"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="acc-api-hash">API Hash</Label>
              <Input
                id="acc-api-hash"
                value={apiHash}
                onChange={(e) => setApiHash(e.target.value)}
                placeholder="a1b2c3d4e5f6..."
              />
            </div>
          </div>

          {error && <p className="text-sm text-rose-400 mt-4">{error}</p>}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
            >
              Отмена
            </Button>
            <Button type="submit" disabled={saving}>
              {saving && <Loader2 size={16} className="animate-spin" />}
              Добавить
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
