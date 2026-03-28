"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { setToken } from "@/lib/auth";
import { API_URL } from "@/lib/constants";
import { Loader2 } from "lucide-react";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [shake, setShake] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Ошибка авторизации");
      }

      const data = await res.json();
      setToken(data.access_token);
      router.push(redirect);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка соединения");
      setShake(true);
      setTimeout(() => setShake(false), 500);
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      className="w-full max-w-sm"
      animate={shake ? { x: [-8, 8, -6, 6, -3, 3, 0] } : {}}
      transition={{ duration: 0.4 }}
    >
      <div className="rounded-xl border border-sg-border bg-sg-surface p-8">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="h-9 w-9 rounded-lg bg-emerald-DEFAULT flex items-center justify-center">
            <svg
              viewBox="0 0 16 16"
              fill="none"
              className="h-4.5 w-4.5 text-sg-base"
            >
              <path
                d="M8 1L14 5V11L8 15L2 11V5L8 1Z"
                fill="currentColor"
              />
              <path
                d="M8 5L11 7V11L8 13L5 11V7L8 5Z"
                fill="#08090d"
                fillOpacity="0.3"
              />
            </svg>
          </div>
          <span className="font-semibold text-lg text-foreground">
            Signal Grid
          </span>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-muted-foreground mb-1.5">
              Email
            </label>
            <Input
              type="email"
              placeholder="admin@signalgrid.ru"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm text-muted-foreground mb-1.5">
              Пароль
            </label>
            <Input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <p className="text-sm text-rose-400 text-center">{error}</p>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Вход...
              </>
            ) : (
              "Войти"
            )}
          </Button>
        </form>
      </div>
    </motion.div>
  );
}
