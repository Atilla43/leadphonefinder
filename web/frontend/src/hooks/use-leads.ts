import useSWR from "swr";
import { fetcher } from "@/lib/api-client";
import type { LeadsResponse, LeadStats } from "@/lib/types";

export function useLeads(params?: {
  status?: string;
  category?: string;
  search?: string;
  sort_by?: string;
  offset?: number;
  limit?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.category) sp.set("category", params.category);
  if (params?.search) sp.set("search", params.search);
  if (params?.sort_by) sp.set("sort_by", params.sort_by);
  if (params?.offset) sp.set("offset", String(params.offset));
  if (params?.limit) sp.set("limit", String(params.limit));

  const qs = sp.toString();
  return useSWR<LeadsResponse>(
    `/api/leads${qs ? `?${qs}` : ""}`,
    fetcher,
    { refreshInterval: 30_000 }
  );
}

export function useLeadStats() {
  return useSWR<LeadStats>("/api/leads/stats", fetcher, {
    refreshInterval: 30_000,
  });
}
