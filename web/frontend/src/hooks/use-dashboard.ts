import useSWR from "swr";
import { fetcher } from "@/lib/api-client";
import type { DashboardStats, FunnelData, TimelineData } from "@/lib/types";

export function useDashboardStats() {
  return useSWR<DashboardStats>("/api/dashboard/stats", fetcher, {
    refreshInterval: 30_000,
  });
}

export function useFunnel() {
  return useSWR<FunnelData>("/api/dashboard/funnel", fetcher, {
    refreshInterval: 30_000,
  });
}

export function useTimeline(days = 30, campaignId?: string) {
  const params = new URLSearchParams({ days: String(days) });
  if (campaignId) params.set("campaign_id", campaignId);

  return useSWR<TimelineData>(
    `/api/dashboard/timeline?${params}`,
    fetcher,
    { refreshInterval: 60_000 }
  );
}
