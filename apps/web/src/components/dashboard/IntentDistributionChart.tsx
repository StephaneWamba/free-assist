"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"
import { INTENT_LABELS, INTENT_COLORS } from "@/types/assistant"
import { useIntentDistribution } from "@/hooks/useDashboardStats"
import type { IntentBucket } from "@/lib/api"

const CustomTooltip = ({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload: IntentBucket }>
}) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null
  return (
    <div className="rounded-lg border border-[#2a2a2a] bg-[#1a1a1a] px-3 py-2 text-xs shadow-xl">
      <p className="font-medium text-zinc-100">{INTENT_LABELS[d.intent] ?? d.intent}</p>
      <p className="mt-1 text-zinc-400">
        {d.count.toLocaleString("fr-FR")} tickets ({d.pct}%)
      </p>
    </div>
  )
}

export function IntentDistributionChart() {
  const { data, isLoading } = useIntentDistribution()
  const empty = !isLoading && (!data || data.length === 0)

  return (
    <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
      <div className="mb-5">
        <h2 className="text-sm font-semibold text-white">Distribution des intentions</h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          {data
            ? `${data.reduce((s, d) => s + d.count, 0).toLocaleString("fr-FR")} tickets classifiés`
            : "Chargement…"}
        </p>
      </div>

      {empty ? (
        <div className="flex h-[280px] items-center justify-center text-sm text-zinc-600">
          Aucun ticket analysé — utilisez l&apos;assistant pour commencer
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart
            data={data ?? []}
            layout="vertical"
            margin={{ left: 8, right: 24, top: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fill: "#71717a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => v.toLocaleString("fr-FR")}
            />
            <YAxis
              type="category"
              dataKey="intent"
              width={130}
              tick={{ fill: "#71717a", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: string) => INTENT_LABELS[v] ?? v}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
            <Bar dataKey="count" radius={[0, 4, 4, 0]}>
              {(data ?? []).map((entry) => (
                <Cell
                  key={entry.intent}
                  fill={INTENT_COLORS[entry.intent] ?? "#71717a"}
                  opacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
