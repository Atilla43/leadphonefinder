"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Search, MessageSquare } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useConversations } from "@/hooks/use-conversations";
import { ConversationList } from "@/components/conversations/conversation-list";
import { ChatView } from "@/components/conversations/chat-view";

const STATUS_TABS = [
  { value: "", label: "Все" },
  { value: "talking", label: "В процессе" },
  { value: "warm,warm_confirmed", label: "Тёплые" },
  { value: "rejected", label: "Отказы" },
  { value: "sent", label: "Отправлено" },
  { value: "no_response", label: "Без ответа" },
];

export default function ConversationsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<{
    campaignId: string;
    phone: string;
  } | null>(null);

  const { data, isLoading } = useConversations({
    status: statusFilter || undefined,
    search: search || undefined,
    limit: 50,
  });

  return (
    <div className="h-screen flex flex-col">
      {/* Page header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="px-8 pt-8 pb-4 shrink-0"
      >
        <h1 className="text-2xl font-semibold text-foreground mb-1">
          Диалоги
        </h1>
        <p className="text-muted-foreground text-sm">
          История переписки с лидами
        </p>
      </motion.div>

      {/* Split panel */}
      <div className="flex-1 flex min-h-0 mx-8 mb-8 rounded-xl border border-sg-border bg-sg-surface overflow-hidden">
        {/* Left panel - conversations list */}
        <div className="w-80 shrink-0 border-r border-sg-border flex flex-col">
          {/* Search */}
          <div className="p-3 border-b border-sg-border">
            <div className="relative">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                placeholder="Поиск..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 h-8 text-sm"
              />
            </div>
          </div>

          {/* Status tabs */}
          <div className="px-3 py-2 border-b border-sg-border flex gap-1 overflow-x-auto">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setStatusFilter(tab.value)}
                className={`px-2.5 py-1 rounded-md text-xs whitespace-nowrap transition-colors ${
                  statusFilter === tab.value
                    ? "bg-emerald-DEFAULT/10 text-emerald-400"
                    : "text-muted-foreground hover:text-foreground hover:bg-sg-hover"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="p-4 space-y-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-16 rounded bg-sg-hover animate-pulse"
                  />
                ))}
              </div>
            ) : (
              <ConversationList
                conversations={data?.conversations || []}
                selectedCampaignId={selected?.campaignId ?? null}
                selectedPhone={selected?.phone ?? null}
                onSelect={(campaignId, phone) =>
                  setSelected({ campaignId, phone })
                }
              />
            )}
          </div>

          {/* Count */}
          {data && (
            <div className="px-4 py-2 border-t border-sg-border text-xs text-muted-foreground">
              {data.total} диалогов
            </div>
          )}
        </div>

        {/* Right panel - chat */}
        <div className="flex-1 flex flex-col">
          {selected ? (
            <ChatView
              campaignId={selected.campaignId}
              phone={selected.phone}
            />
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
              <MessageSquare
                size={40}
                className="mb-3 opacity-30"
              />
              <p className="text-sm">Выберите диалог</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
