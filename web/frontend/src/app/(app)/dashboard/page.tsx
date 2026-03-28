"use client";

import { motion } from "framer-motion";
import { KpiCards } from "@/components/dashboard/kpi-cards";
import { TimelineChart } from "@/components/dashboard/timeline-chart";
import { FunnelChart } from "@/components/dashboard/funnel-chart";
import { CampaignsTable } from "@/components/dashboard/campaigns-table";
import { useDashboardStats, useFunnel, useTimeline } from "@/hooks/use-dashboard";
import { useCampaigns } from "@/hooks/use-campaigns";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: funnel, isLoading: funnelLoading } = useFunnel();
  const { data: timeline, isLoading: timelineLoading } = useTimeline();
  const { data: campaignsData, isLoading: campaignsLoading } = useCampaigns();

  return (
    <div className="p-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-8"
      >
        <h1 className="text-2xl font-semibold text-foreground mb-1">
          Дашборд
        </h1>
        <p className="text-muted-foreground text-sm">
          Аналитика и статистика рассылок
        </p>
      </motion.div>

      {/* KPI row */}
      <KpiCards stats={stats} isLoading={statsLoading} />

      {/* Charts row */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3">
          <TimelineChart points={timeline?.points} isLoading={timelineLoading} />
        </div>
        <div className="lg:col-span-2">
          <FunnelChart stages={funnel?.stages} isLoading={funnelLoading} />
        </div>
      </div>

      {/* Campaigns table */}
      <div className="mt-6">
        <CampaignsTable
          campaigns={campaignsData?.campaigns}
          isLoading={campaignsLoading}
        />
      </div>
    </div>
  );
}
