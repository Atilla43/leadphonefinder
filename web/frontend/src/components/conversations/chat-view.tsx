"use client";

import { motion } from "framer-motion";
import { useConversation } from "@/hooks/use-conversations";
import { StatusBadge } from "@/components/ui/status-dot";
import { cn } from "@/lib/utils";
import {
  Building2,
  User,
  MapPin,
  Star,
  Globe,
  Phone,
} from "lucide-react";
import { formatPhoneMasked } from "@/lib/formatters";

interface ChatViewProps {
  campaignId: string;
  phone: string;
}

export function ChatView({ campaignId, phone }: ChatViewProps) {
  const { data, isLoading } = useConversation(campaignId, phone);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="h-6 w-6 border-2 border-emerald-DEFAULT border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        Диалог не найден
      </div>
    );
  }

  const { recipient, messages, campaign } = data;

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Chat header */}
      <div className="px-5 py-3 border-b border-sg-border flex items-center justify-between shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium text-foreground">
              {recipient.company_name}
            </h3>
            <StatusBadge status={recipient.status} type="recipient" />
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {campaign.name}
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-3">
        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: i * 0.03 }}
            className={cn(
              "flex",
              msg.role === "assistant" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[75%] rounded-xl px-4 py-2.5 text-sm leading-relaxed",
                msg.role === "assistant"
                  ? "bg-emerald-DEFAULT/15 text-foreground rounded-br-sm"
                  : "bg-sg-elevated text-foreground rounded-bl-sm border border-sg-border"
              )}
            >
              {msg.content}
            </div>
          </motion.div>
        ))}

        {!messages.length && (
          <div className="text-center text-muted-foreground text-sm py-8">
            Нет сообщений
          </div>
        )}
      </div>

      {/* Recipient info panel */}
      <div className="border-t border-sg-border p-4 shrink-0">
        <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
          {recipient.contact_name && (
            <span className="inline-flex items-center gap-1.5">
              <User size={12} /> {recipient.contact_name}
            </span>
          )}
          <span className="inline-flex items-center gap-1.5">
            <Phone size={12} /> {formatPhoneMasked(recipient.phone)}
          </span>
          {recipient.category && (
            <span className="inline-flex items-center gap-1.5">
              <Building2 size={12} /> {recipient.category}
            </span>
          )}
          {recipient.address && (
            <span className="inline-flex items-center gap-1.5">
              <MapPin size={12} /> {recipient.address}
            </span>
          )}
          {recipient.rating && (
            <span className="inline-flex items-center gap-1.5">
              <Star size={12} /> {recipient.rating}
            </span>
          )}
          {recipient.website && (
            <span className="inline-flex items-center gap-1.5">
              <Globe size={12} /> {recipient.website}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
