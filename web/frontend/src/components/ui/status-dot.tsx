"use client";

import { cn } from "@/lib/utils";
import {
  RECIPIENT_STATUS_CONFIG,
  CAMPAIGN_STATUS_CONFIG,
  STATUS_COLORS,
} from "@/lib/constants";
import { Badge } from "./badge";

interface StatusBadgeProps {
  status: string;
  type?: "recipient" | "campaign";
  className?: string;
}

export function StatusBadge({
  status,
  type = "recipient",
  className,
}: StatusBadgeProps) {
  const config =
    type === "campaign"
      ? CAMPAIGN_STATUS_CONFIG[status]
      : RECIPIENT_STATUS_CONFIG[status];

  if (!config) {
    return (
      <Badge variant="gray" className={className}>
        {status}
      </Badge>
    );
  }

  const colors = STATUS_COLORS[config.color] || STATUS_COLORS.gray;

  return (
    <Badge
      variant={config.color as "emerald" | "cyan" | "amber" | "rose" | "gray"}
      className={className}
    >
      <span className="relative flex h-2 w-2">
        {config.ping && (
          <span
            className={cn(
              "absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping-dot",
              colors.dot
            )}
          />
        )}
        <span
          className={cn(
            "relative inline-flex h-2 w-2 rounded-full",
            colors.dot
          )}
        />
      </span>
      {config.label}
    </Badge>
  );
}
