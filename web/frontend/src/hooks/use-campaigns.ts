import useSWR from "swr";
import { fetcher } from "@/lib/api-client";
import type {
  CampaignListResponse,
  CampaignDetail,
  RecipientsResponse,
} from "@/lib/types";

export function useCampaigns(status?: string) {
  const params = status ? `?status=${status}` : "";
  return useSWR<CampaignListResponse>(
    `/api/campaigns${params}`,
    fetcher,
    { refreshInterval: 30_000 }
  );
}

export function useCampaign(id: string | null) {
  return useSWR<CampaignDetail>(
    id ? `/api/campaigns/${id}` : null,
    fetcher,
    { refreshInterval: 15_000 }
  );
}

export function useRecipients(
  campaignId: string | null,
  params?: { status?: string; search?: string; offset?: number; limit?: number }
) {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.search) sp.set("search", params.search);
  if (params?.offset) sp.set("offset", String(params.offset));
  if (params?.limit) sp.set("limit", String(params.limit));

  const qs = sp.toString();
  return useSWR<RecipientsResponse>(
    campaignId
      ? `/api/campaigns/${campaignId}/recipients${qs ? `?${qs}` : ""}`
      : null,
    fetcher,
    { refreshInterval: 15_000 }
  );
}
