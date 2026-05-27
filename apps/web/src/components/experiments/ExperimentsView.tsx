"use client"

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { useExperiments, useExperimentRuns } from "@/hooks/useExperiments"
import { useState } from "react"
import type { MLflowRun } from "@/lib/api"

function StatusDot({ status }: { status: string }) {
  const styles: Record<string, string> = {
    FINISHED: "bg-emerald-500",
    RUNNING:  "bg-amber-400 animate-pulse",
    FAILED:   "bg-red-500",
  }
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${styles[status] ?? "bg-zinc-500"}`}
    />
  )
}

function metricValue(run: MLflowRun, key: string): string {
  const v = run.data?.metrics?.[key]
  return v != null ? v.toFixed(3) : "—"
}

function duration(run: MLflowRun): string {
  if (!run.info.end_time || !run.info.start_time) return "En cours"
  const ms = run.info.end_time - run.info.start_time
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

function formatDate(ts: number): string {
  return new Date(ts).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function ExperimentsView() {
  const { data: expData, isLoading: expLoading } = useExperiments()
  const experiments = expData?.experiments ?? []

  const firstExpId = experiments[0]?.experiment_id ?? null
  const [selectedExp, setSelectedExp] = useState<string | null>(null)
  const activeExp = selectedExp ?? firstExpId

  const { data: runsData, isLoading: runsLoading } = useExperimentRuns(activeExp)
  const runs = runsData?.runs ?? []

  // Build training curve from metric history of best run
  const bestRun = runs
    .filter((r) => r.info.status === "FINISHED")
    .sort((a, b) => (b.data?.metrics?.["val_f1"] ?? 0) - (a.data?.metrics?.["val_f1"] ?? 0))[0]

  // Simple epoch curve from available metrics (MLflow stores final values)
  const curve = bestRun
    ? [
        {
          epoch: "Final",
          train_loss: bestRun.data?.metrics?.["train_loss"] ?? null,
          val_f1: bestRun.data?.metrics?.["val_f1"] ?? bestRun.data?.metrics?.["eval_f1"] ?? null,
        },
      ]
    : []

  return (
    <div className="space-y-5">
      {/* Experiment selector */}
      {experiments.length > 1 && (
        <div className="flex items-center gap-3">
          <span className="text-xs text-zinc-500">Expérience :</span>
          <div className="flex gap-2">
            {experiments.map((exp) => (
              <button
                key={exp.experiment_id}
                onClick={() => setSelectedExp(exp.experiment_id)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  activeExp === exp.experiment_id
                    ? "bg-[#E2001A]/10 text-[#E2001A] ring-1 ring-[#E2001A]/20"
                    : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {exp.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Runs table */}
      <div className="rounded-xl border border-[#1e1e1e] bg-[#141414]">
        <div className="px-5 py-4 border-b border-[#1e1e1e]">
          <h2 className="text-sm font-semibold text-white">Runs d&apos;entraînement</h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            {activeExp
              ? `Expérience : ${experiments.find((e) => e.experiment_id === activeExp)?.name ?? activeExp}`
              : "Chargement…"}
          </p>
        </div>

        {(expLoading || runsLoading) && (
          <div className="px-5 py-6 text-xs text-zinc-600">Connexion à MLflow…</div>
        )}

        {!runsLoading && runs.length === 0 && !expLoading && (
          <div className="px-5 py-6 text-xs text-zinc-600">
            Aucun run — lancez un entraînement pour voir les résultats ici
          </div>
        )}

        {runs.length > 0 && (
          <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[560px]">
            <thead>
              <tr className="border-b border-[#1e1e1e]">
                {["Run", "Statut", "F1 Macro", "Accuracy", "Durée", "Date"].map((h) => (
                  <th
                    key={h}
                    className="px-5 py-3 text-left text-[11px] font-semibold text-zinc-500 uppercase tracking-widest"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e1e1e]">
              {runs.map((run) => (
                <tr key={run.info.run_id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-5 py-3.5">
                    <p className="text-[13px] font-medium text-zinc-200">{run.info.run_name}</p>
                    <p className="text-[11px] font-mono text-zinc-600">
                      {run.info.run_id.slice(0, 8)}
                    </p>
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <StatusDot status={run.info.status} />
                      <span className="text-[12px] text-zinc-400 capitalize">
                        {run.info.status.toLowerCase()}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 font-mono font-semibold text-[13px] text-emerald-400">
                    {metricValue(run, "val_f1") !== "—"
                      ? metricValue(run, "val_f1")
                      : metricValue(run, "eval_f1")}
                  </td>
                  <td className="px-5 py-3.5 font-mono font-semibold text-[13px] text-zinc-200">
                    {metricValue(run, "accuracy")}
                  </td>
                  <td className="px-5 py-3.5 text-[12px] text-zinc-500 font-mono">
                    {duration(run)}
                  </td>
                  <td className="px-5 py-3.5 text-[12px] text-zinc-600">
                    {formatDate(run.info.start_time)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>

      {/* Training curve — shown only when we have metric data */}
      {curve.length > 0 && (
        <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
          <h2 className="text-sm font-semibold text-white mb-1">Métriques finales</h2>
          <p className="text-xs text-zinc-500 mb-5">
            {bestRun?.info.run_name} · Loss + F1
          </p>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={curve} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" />
              <XAxis
                dataKey="epoch"
                tick={{ fill: "#71717a", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a1a",
                  border: "1px solid #2a2a2a",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "#fff" }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: "#71717a" }} />
              <Line
                type="monotone"
                dataKey="train_loss"
                stroke="#E2001A"
                strokeWidth={2}
                dot={{ fill: "#E2001A", r: 5 }}
                name="Train Loss"
              />
              <Line
                type="monotone"
                dataKey="val_f1"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ fill: "#10b981", r: 5 }}
                name="Val F1"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
