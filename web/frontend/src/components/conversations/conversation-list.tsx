"use client";

import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/status-dot";
import { formatRelativeTime } from "@/lib/formatters";
import type { ConversationPreview } from "@/lib/types";

interface ConversationListProps {
  conversations: ConversationPreview[];
  selectedCampaignId: string | null;
  selectedPhone: string | null;
  onSelect: (campaignId: string, phone: string) => void;
}

export function ConversationList({
  conversations,
  selectedCampaignId,
  selectedPhone,
  onSelect,
}: ConversationListProps) {
  if (!conversations.length) {
    return (
      <div className="p-8 text-center text-muted-foreground text-sm">
        Нет диалогов
      </div>
    );
  }

  return (
    <div className="divide-y divide-sg-border">
      {conversations.map((c) => {
        const isActive =
          c.campaign_id === selectedCampaignId && c.phone === selectedPhone;

        return (
          <button
            key={`${c.campaign_id}-${c.phone}`}
            onClick={() => onSelect(c.campaign_id, c.phone)}
            className={cn(
              "w-full text-left px-4 py-3 transition-colors",
              isActive
                ? "bg-emerald-DEFAULT/5 border-l-2 border-l-emerald-DEFAULT"
                : "hover:bg-sg-hover border-l-2 border-l-transparent"
            )}
          >
            <div className="flex items-start justify-between gap-2 mb-1">
              <span className="text-sm font-medium text-foreground truncate">
                {c.company_name}
              </span>
              {c.last_message_at && (
                <span className="text-[11px] text-muted-foreground shrink-0">
                  {formatRelativeTime(c.last_message_at)}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 mb-1.5">
              {c.contact_name && (
                <span className="text-xs text-muted-foreground truncate">
                  {c.contact_name}
                </span>
              )}
              <StatusBadge status={c.status} type="recipient" />
            </div>

            {c.last_message && (
              <p className="text-xs text-muted-foreground line-clamp-1">
                {c.last_message.role === "assistant" && (
                  <span className="text-emerald-400/70">Вы: </span>
                )}
                {c.last_message.content}
              </p>
            )}
          </button>
        );
      })}
    </div>
  );
}
