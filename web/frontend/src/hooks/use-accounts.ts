import useSWR from "swr";
import { apiFetch, fetcher } from "@/lib/api-client";

export interface AccountItem {
  phone: string;
  phone_masked: string;
  active: boolean;
  connected: boolean;
  session_name: string;
  sent_today: number;
  daily_limit: number;
}

interface AccountsResponse {
  accounts: AccountItem[];
  total_accounts: number;
  active_accounts: number;
  connected_accounts: number;
}

export function useAccounts() {
  return useSWR<AccountsResponse>("/api/accounts", fetcher, {
    refreshInterval: 10_000,
  });
}

export async function addAccount(phone: string, apiId: number, apiHash: string) {
  return apiFetch<{ phone: string; session_name: string; message: string }>(
    "/api/accounts",
    {
      method: "POST",
      body: JSON.stringify({ phone, api_id: apiId, api_hash: apiHash }),
    }
  );
}

export async function removeAccount(phone: string) {
  return apiFetch<{ phone: string; message: string }>(
    `/api/accounts/${encodeURIComponent(phone)}`,
    { method: "DELETE" }
  );
}

export async function toggleAccount(phone: string) {
  return apiFetch<{ phone: string; active: boolean; message: string }>(
    `/api/accounts/${encodeURIComponent(phone)}/toggle`,
    { method: "PUT" }
  );
}

export async function startConnect(phone: string) {
  return apiFetch<{ phone_code_hash: string; message: string }>(
    `/api/accounts/${encodeURIComponent(phone)}/connect`,
    { method: "POST" }
  );
}

export async function verifyConnect(
  phone: string,
  code: string,
  phoneCodeHash: string,
  password?: string
) {
  return apiFetch<{ success: boolean; needs_2fa: boolean; message: string }>(
    `/api/accounts/${encodeURIComponent(phone)}/verify`,
    {
      method: "POST",
      body: JSON.stringify({
        code,
        phone_code_hash: phoneCodeHash,
        password: password || null,
      }),
    }
  );
}
