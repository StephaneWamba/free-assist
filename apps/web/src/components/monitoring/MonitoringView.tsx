"use client"

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { AlertTriangle, CheckCircle2, Info } from "lucide-react"
import { useMonitoringAlerts, useDriftData } from "@/hooks/useMonitoring"
import { INTENT_LABELS } from "@/types/assistant"

const INTENT_STROKE: Record<string, string> = {
  BOX_CONNECTIVITY:  "#3b82f6",
  BILLING_DISPUTE:   "#ef4444",
  TECHNICAL_OUTAGE:  "#f97316",
  BOX_REBOOT:        "#8b5cf6",
  SPEED_ISSUE:       "#06b6d4",
  MOBILE_PORTABILITY:"#10b981",
  CONTRACT_CHANGE:   "#f59e0b",
  CANCELLATION:      "#E2001A",
  EQUIPMENT_RETURN:  "#64748b",
  OTHER:             "#71717a",
}

function AlertIcon({ level }: { level: string }) {
  if (level === "warning") return <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
  if (level === "info")    return <Info className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
  return <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
}

function alertStyle(level: string) {
  if (level === "warning") return "bg-amber-500/5 border border-amber-500/20"
  if (level === "info")    return "bg-blue-500/5 border border-blue-500/10"
  return "bg-emerald-500/5 border border-emerald-500/10"
}

export function MonitoringView() {
  const { data: alerts, isLoading: alertsLoading } = useMonitoringAlerts()
  const { data: drift, isLoading: driftLoading } = useDriftData(3)

  const firstPoint = drift?.[0]
  const driftIntents = firstPoint
    ? Object.keys(firstPoint).filter((k) => k !== "date")
    : []

  return (
    <div className="space-y-5">
      {/* Alerts */}
      <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Alertes actives</h2>
        {alertsLoading && (
          <p className="text-xs text-zinc-600">Chargement…</p>
        )}
        {!alertsLoading && (!alerts || alerts.length === 0) && (
          <p className="text-xs text-zinc-600">Aucune alerte</p>
        )}
        <div className="space-y-3">
          {alerts?.map((alert, i) => (
            <div key={i} className={`flex items-start gap-3 rounded-lg p-3.5 ${alertStyle(alert.level)}`}>
              <AlertIcon level={alert.level} />
              <div>
                <p className="text-[13px] text-zinc-200">{alert.message}</p>
                {alert.intent && (
                  <p className="text-[11px] text-zinc-500 mt-0.5">
                    {INTENT_LABELS[alert.intent] ?? alert.intent}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Drift chart */}
      <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
        <div className="mb-5">
          <h2 className="text-sm font-semibold text-white">
            Distribution des intentions (7 jours)
          </h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            Détection de dérive · top 3 intentions
          </p>
        </div>

        {driftLoading && (
          <div className="flex h-[260px] items-center justify-center text-xs text-zinc-600">
            Chargement…
          </div>
        )}

        {!driftLoading && (!drift || drift.length === 0) && (
          <div className="flex h-[260px] items-center justify-center text-sm text-zinc-600">
            Pas encore de données sur 7 jours
          </div>
        )}

        {drift && drift.length > 0 && (
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={drift} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <defs>
                {driftIntents.map((intent, i) => (
                  <linearGradient key={intent} id={`g${i}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={INTENT_STROKE[intent] ?? "#71717a"} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={INTENT_STROKE[intent] ?? "#71717a"} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#71717a", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#71717a", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                unit="%"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a1a",
                  border: "1px solid #2a2a2a",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(v: number) => [`${v}%`]}
              />
              {driftIntents.map((intent, i) => (
                <Area
                  key={intent}
                  type="monotone"
                  dataKey={intent}
                  stroke={INTENT_STROKE[intent] ?? "#71717a"}
                  fill={`url(#g${i})`}
                  strokeWidth={2}
                  name={INTENT_LABELS[intent] ?? intent}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
