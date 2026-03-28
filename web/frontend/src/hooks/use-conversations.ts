import useSWR from "swr";
import { fetcher } from "@/lib/api-client";
import type { ConversationsResponse, ConversationDetail } from "@/lib/types";

export function useConversations(params?: {
  status?: string;
  campaign_id?: string;
  search?: string;
  offset?: number;
  limit?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.campaign_id) sp.set("campaign_id", params.campaign_id);
  if (params?.search) sp.set("search", params.search);
  if (params?.offset) sp.set("offset", String(params.offset));
  if (params?.limit) sp.set("limit", String(params.limit));

  const qs = sp.toString();
  return useSWR<ConversationsResponse>(
    `/api/conversations${qs ? `?${qs}` : ""}`,
    fetcher,
    { refreshInterval: 10_000 }
  );
}

export function useConversation(
  campaignId: string | null,
  phone: string | null
) {
  return useSWR<ConversationDetail>(
    campaignId && phone
      ? `/api/conversations/${campaignId}/${phone}`
      : null,
    fetcher,
    { refreshInterval: 5_000 }
  );
}
