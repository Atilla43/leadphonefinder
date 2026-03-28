"use client";

import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { ChatView } from "@/components/conversations/chat-view";

export default function ConversationDetailPage() {
  const { campaignId, phone } = useParams<{
    campaignId: string;
    phone: string;
  }>();
  const router = useRouter();

  return (
    <div className="h-screen flex flex-col">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="px-8 pt-8 pb-4 shrink-0"
      >
        <button
          onClick={() => router.push("/conversations")}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-2"
        >
          <ArrowLeft size={14} />
          Все диалоги
        </button>
      </motion.div>

      <div className="flex-1 mx-8 mb-8 rounded-xl border border-sg-border bg-sg-surface overflow-hidden flex flex-col">
        <ChatView campaignId={campaignId} phone={decodeURIComponent(phone)} />
      </div>
    </div>
  );
}
