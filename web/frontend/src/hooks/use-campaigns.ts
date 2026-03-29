import useSWR from "swr";
import { apiFetch, fetcher } from "@/lib/api-client";
import type {
  CampaignListResponse,
  CampaignDetail,
  CampaignActionResponse,
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

// ─── Campaign lifecycle mutations ───

export async function launchCampaign(id: string): Promise<CampaignActionResponse> {
  return apiFetch<CampaignActionResponse>(`/api/campaigns/${id}/launch`, {
    method: "POST",
  });
}

export async function pauseCampaign(id: string): Promise<CampaignActionResponse> {
  return apiFetch<CampaignActionResponse>(`/api/campaigns/${id}/pause`, {
    method: "POST",
  });
}

export async function resumeCampaign(id: string): Promise<CampaignActionResponse> {
  return apiFetch<CampaignActionResponse>(`/api/campaigns/${id}/resume`, {
    method: "POST",
  });
}

export async function cancelCampaign(id: string): Promise<CampaignActionResponse> {
  return apiFetch<CampaignActionResponse>(`/api/campaigns/${id}/cancel`, {
    method: "POST",
  });
}

export async function deleteCampaign(id: string): Promise<CampaignActionResponse> {
  return apiFetch<CampaignActionResponse>(`/api/campaigns/${id}`, {
    method: "DELETE",
  });
}
