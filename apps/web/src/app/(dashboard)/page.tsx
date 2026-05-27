"use client"

import dynamic from "next/dynamic"
import {
  MessageSquareText,
  CheckCircle2,
  Clock,
  TrendingUp,
} from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { KPICard } from "@/components/dashboard/KPICard"
import { RecentTicketsFeed } from "@/components/dashboard/RecentTicketsFeed"
import { ModelBenchmarkTable } from "@/components/dashboard/ModelBenchmarkTable"
import { useDashboardKPIs } from "@/hooks/useDashboardStats"

const IntentDistributionChart = dynamic(
  () => import("@/components/dashboard/IntentDistributionChart").then(m => m.IntentDistributionChart),
  { ssr: false, loading: () => <div className="h-[340px] rounded-xl border border-[#1e1e1e] bg-[#141414] animate-pulse" /> },
)

export default function DashboardPage() {
  const { data: kpis } = useDashboardKPIs()

  return (
    <AppShell
      title="Dashboard"
      subtitle="Vue d'ensemble de la plateforme FreeAssist · Support technique"
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KPICard
          label="Tickets analysés"
          value={kpis ? kpis.total_tickets.toLocaleString("fr-FR") : "—"}
          subtitle="Depuis le démarrage"
          icon={MessageSquareText}
          trend={undefined}
          variant="default"
        />
        <KPICard
          label="Taux de résolution"
          value={kpis ? `${kpis.resolution_rate}%` : "—"}
          subtitle="Confiance ≥ 50%"
          icon={CheckCircle2}
          trend={undefined}
          variant="success"
        />
        <KPICard
          label="Latence médiane"
          value={kpis ? `${kpis.median_latency_ms}ms` : "—"}
          subtitle="RAG + classification"
          icon={Clock}
          trend={undefined}
          variant="default"
        />
        <KPICard
          label="Confiance moyenne"
          value={kpis ? kpis.avg_confidence.toFixed(3) : "—"}
          subtitle="Classifier intent"
          icon={TrendingUp}
          trend={undefined}
          variant="success"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <IntentDistributionChart />
        </div>
        <div className="lg:col-span-1">
          <RecentTicketsFeed />
        </div>
      </div>

      <div className="mt-6">
        <ModelBenchmarkTable />
      </div>
    </AppShell>
  )
}
