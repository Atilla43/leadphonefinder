"use client";

import { useState } from "react";
import { Loader2, KeyRound } from "lucide-react";
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
import { startConnect, verifyConnect } from "@/hooks/use-accounts";

interface AccountOtpDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  phone: string;
  onSuccess: () => void;
}

type Step = "send_code" | "enter_code" | "enter_2fa";

export function AccountOtpDialog({
  open,
  onOpenChange,
  phone,
  onSuccess,
}: AccountOtpDialogProps) {
  const [step, setStep] = useState<Step>("send_code");
  const [phoneCodeHash, setPhoneCodeHash] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleOpenChange(isOpen: boolean) {
    if (!isOpen) {
      setStep("send_code");
      setPhoneCodeHash("");
      setCode("");
      setPassword("");
      setError("");
    }
    onOpenChange(isOpen);
  }

  async function handleSendCode() {
    setLoading(true);
    setError("");
    try {
      const result = await startConnect(phone);
      setPhoneCodeHash(result.phone_code_hash);
      setStep("enter_code");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка отправки кода");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyCode() {
    setLoading(true);
    setError("");
    try {
      const result = await verifyConnect(phone, code, phoneCodeHash);
      if (result.success) {
        handleOpenChange(false);
        onSuccess();
      } else if (result.needs_2fa) {
        setStep("enter_2fa");
      } else {
        setError(result.message || "Неизвестная ошибка");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка верификации");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify2FA() {
    setLoading(true);
    setError("");
    try {
      const result = await verifyConnect(phone, code, phoneCodeHash, password);
      if (result.success) {
        handleOpenChange(false);
        onSuccess();
      } else {
        setError(result.message || "Неверный пароль");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка 2FA");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound size={18} className="text-emerald-400" />
            Подключение {phone}
          </DialogTitle>
          <DialogDescription>
            {step === "send_code" && "Отправим код авторизации на номер"}
            {step === "enter_code" && "Введите код из SMS или Telegram"}
            {step === "enter_2fa" && "Требуется пароль двухфакторной аутентификации"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {step === "send_code" && (
            <p className="text-sm text-muted-foreground">
              Telegram отправит код подтверждения на {phone}. Проверьте SMS или приложение Telegram.
            </p>
          )}

          {step === "enter_code" && (
            <div className="space-y-2">
              <Label htmlFor="otp-code">Код подтверждения</Label>
              <Input
                id="otp-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="12345"
                autoFocus
              />
            </div>
          )}

          {step === "enter_2fa" && (
            <div className="space-y-2">
              <Label htmlFor="otp-password">Пароль 2FA</Label>
              <Input
                id="otp-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Пароль двухфакторной аутентификации"
                autoFocus
              />
            </div>
          )}
        </div>

        {error && <p className="text-sm text-rose-400 mt-4">{error}</p>}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
          >
            Отмена
          </Button>
          {step === "send_code" && (
            <Button onClick={handleSendCode} disabled={loading}>
              {loading && <Loader2 size={16} className="animate-spin" />}
              Отправить код
            </Button>
          )}
          {step === "enter_code" && (
            <Button onClick={handleVerifyCode} disabled={loading || !code.trim()}>
              {loading && <Loader2 size={16} className="animate-spin" />}
              Подтвердить
            </Button>
          )}
          {step === "enter_2fa" && (
            <Button onClick={handleVerify2FA} disabled={loading || !password.trim()}>
              {loading && <Loader2 size={16} className="animate-spin" />}
              Войти
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
