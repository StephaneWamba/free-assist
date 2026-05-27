"use client"

import { useState } from "react"
import {
  CheckCircle2, AlertTriangle, Loader2, Dumbbell,
  BarChart3, Target, Clock, TrendingUp, ChevronDown, ChevronUp,
} from "lucide-react"
import { useExperiments, useExperimentRuns } from "@/hooks/useExperiments"
import type { MLflowRun } from "@/lib/api"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

const INTENTS = [
  "BOX_CONNECTIVITY", "BOX_REBOOT", "MOBILE_PORTABILITY", "BILLING_DISPUTE",
  "CONTRACT_CHANGE", "TECHNICAL_OUTAGE", "EQUIPMENT_RETURN",
  "SPEED_ISSUE", "CANCELLATION", "OTHER",
]

const INTENT_LABELS: Record<string, string> = {
  BOX_CONNECTIVITY: "Connexion box",
  BOX_REBOOT: "Redémarrage box",
  MOBILE_PORTABILITY: "Portabilité mobile",
  BILLING_DISPUTE: "Litige facturation",
  CONTRACT_CHANGE: "Changement d'offre",
  TECHNICAL_OUTAGE: "Panne technique",
  EQUIPMENT_RETURN: "Retour matériel",
  SPEED_ISSUE: "Problème de débit",
  CANCELLATION: "Résiliation",
  OTHER: "Autre",
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function qualityColor(v: number | undefined): string {
  if (v == null) return "text-zinc-500"
  if (v >= 0.90) return "text-emerald-400"
  if (v >= 0.80) return "text-amber-400"
  return "text-red-400"
}

function qualityLabel(v: number | undefined): string {
  if (v == null) return "—"
  if (v >= 0.90) return "Excellent"
  if (v >= 0.80) return "Acceptable"
  return "À améliorer"
}

function formatDuration(ms: number): string {
  const min = Math.floor(ms / 60000)
  const sec = Math.floor((ms % 60000) / 1000)
  if (min === 0) return `${sec}s`
  return `${min}m ${sec}s`
}

// ---------------------------------------------------------------------------
// Run card
// ---------------------------------------------------------------------------

function RunCard({ run }: { run: MLflowRun }) {
  const [expanded, setExpanded] = useState(false)
  const m = run.data.metrics ?? {}
  const p = run.data.params ?? {}

  const f1Macro   = m["test/f1_macro"]   ?? m["val/f1_macro"]   ?? m["f1_macro"]
  const accuracy  = m["test/accuracy"]   ?? m["val/accuracy"]   ?? m["accuracy"]
  const f1W       = m["test/f1_weighted"] ?? m["val/f1_weighted"] ?? m["f1_weighted"]
  const duration  = run.info.end_time - run.info.start_time
  const isFinished = run.info.status === "FINISHED"

  // Per-class F1 from metrics
  const perClassF1: Record<string, number> = {}
  for (const intent of INTENTS) {
    const key = `test/${intent}/f1`
    if (m[key] != null) perClassF1[intent] = m[key]
  }
  const hasPerClass = Object.keys(perClassF1).length > 0

  return (
    <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] overflow-hidden">
      {/* Header */}
      <div className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span className={`shrink-0 h-2 w-2 rounded-full ${isFinished ? "bg-emerald-400" : "bg-amber-400 animate-pulse"}`} />
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate">
              {run.info.run_name || run.info.run_id.slice(0, 12)}
            </p>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              {isFinished ? "Terminé" : run.info.status} · {formatDuration(duration)}
            </p>
          </div>
        </div>

        {/* Key metrics */}
        <div className="flex items-center gap-4 shrink-0 flex-wrap">
          <div className="text-right">
            <p className={`text-lg font-bold tabular-nums ${qualityColor(f1Macro)}`}>
              {f1Macro != null ? (f1Macro * 100).toFixed(1) : "—"}
            </p>
            <p className="text-[10px] text-zinc-600">F1 macro</p>
          </div>
          <div className="text-right">
            <p className="text-lg font-bold tabular-nums text-zinc-200">
              {accuracy != null ? (accuracy * 100).toFixed(1) : "—"}
            </p>
            <p className="text-[10px] text-zinc-600">Accuracy</p>
          </div>
          {f1Macro != null && (
            <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${
              f1Macro >= 0.90 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : f1Macro >= 0.80 ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
              : "bg-red-500/10 text-red-400 border-red-500/20"
            }`}>
              {qualityLabel(f1Macro)}
            </span>
          )}
          <button
            onClick={() => setExpanded(v => !v)}
            className="text-zinc-600 hover:text-zinc-300 transition-colors"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-[#1e1e1e] px-5 py-4 space-y-4">
          {/* Hyperparams */}
          <div>
            <p className="text-[11px] text-zinc-500 uppercase tracking-wider mb-2">Hyperparamètres</p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                ["Modèle", p["base_model"] ?? "—"],
                ["Epochs", p["epochs"] ?? "—"],
                ["Batch size", p["batch_size"] ?? "—"],
                ["LR", p["lr"] ?? "—"],
                ["Train samples", p["train_samples"] ? Number(p["train_samples"]).toLocaleString("fr-FR") : "—"],
                ["Val samples", p["val_samples"] ? Number(p["val_samples"]).toLocaleString("fr-FR") : "—"],
                ["Test samples", p["test_samples"] ? Number(p["test_samples"]).toLocaleString("fr-FR") : "—"],
                ["FP16", p["fp16"] ?? "—"],
              ].map(([label, value]) => (
                <div key={label as string} className="rounded-lg bg-[#1a1a1a] px-3 py-2">
                  <p className="text-[10px] text-zinc-600">{label}</p>
                  <p className="text-[12px] text-zinc-200 font-mono mt-0.5">{value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Global metrics */}
          <div>
            <p className="text-[11px] text-zinc-500 uppercase tracking-wider mb-2">Métriques globales</p>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "F1 macro", value: f1Macro },
                { label: "F1 weighted", value: f1W },
                { label: "Accuracy", value: accuracy },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-lg bg-[#1a1a1a] px-3 py-2 text-center">
                  <p className={`text-xl font-bold tabular-nums ${qualityColor(value)}`}>
                    {value != null ? (value * 100).toFixed(2) + "%" : "—"}
                  </p>
                  <p className="text-[10px] text-zinc-600 mt-0.5">{label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Per-class F1 */}
          {hasPerClass && (
            <div>
              <p className="text-[11px] text-zinc-500 uppercase tracking-wider mb-2">F1 par intention</p>
              <div className="space-y-1.5">
                {INTENTS.map(intent => {
                  const f1 = perClassF1[intent]
                  const pct = f1 != null ? Math.round(f1 * 100) : null
                  return (
                    <div key={intent} className="flex items-center gap-3">
                      <span className="text-[11px] text-zinc-500 w-40 shrink-0">
                        {INTENT_LABELS[intent] ?? intent}
                      </span>
                      <div className="flex-1 h-1.5 rounded-full bg-[#1e1e1e] overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            (pct ?? 0) >= 90 ? "bg-emerald-500"
                            : (pct ?? 0) >= 80 ? "bg-amber-500"
                            : "bg-red-500"
                          }`}
                          style={{ width: `${pct ?? 0}%` }}
                        />
                      </div>
                      <span className={`text-[11px] font-mono w-10 text-right ${qualityColor(f1)}`}>
                        {pct != null ? `${pct}%` : "—"}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Pipeline steps (static — shows what the script does)
// ---------------------------------------------------------------------------

const PIPELINE_STEPS = [
  { label: "Augmentation GPT-4o-mini", desc: "8 variantes par intention (80 conversations)", icon: Target },
  { label: "Génération des splits", desc: "2000 train · 300 val · 300 test (avec bruit réaliste)", icon: BarChart3 },
  { label: "Fine-tuning CamemBERT", desc: "camembert-base → 10 classes, 8 epochs, FP16, early stopping", icon: Dumbbell },
  { label: "Évaluation test set", desc: "F1 macro · F1 par classe · Matrice de confusion → MLflow", icon: CheckCircle2 },
]

// ---------------------------------------------------------------------------
// Main view
// ---------------------------------------------------------------------------

export function TrainingView() {
  const { data: experiments, isLoading: expLoading } = useExperiments()

  // Find the intent classifier experiment
  const classifierExp = experiments?.experiments?.find(e =>
    e.name.includes("intent") || e.name.includes("classifier") || e.name.includes("freeassist")
  ) ?? experiments?.experiments?.[0]

  const { data: runsData, isLoading: runsLoading } = useExperimentRuns(
    classifierExp?.experiment_id ?? null
  )
  const runs = runsData?.runs ?? []
  const bestRun = runs.find(r => r.info.status === "FINISHED")
  const bestF1  = bestRun?.data?.metrics?.["test/f1_macro"] ?? bestRun?.data?.metrics?.["f1_macro"]

  return (
    <div className="space-y-6">
      {/* Pipeline overview */}
      <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
        <div className="flex items-center gap-2 mb-5">
          <Dumbbell className="h-4 w-4 text-zinc-500" />
          <h2 className="text-sm font-semibold text-white">Pipeline d'entraînement CamemBERT</h2>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {PIPELINE_STEPS.map((step, i) => (
            <div key={i} className="rounded-lg bg-[#1a1a1a] p-3.5 relative">
              <div className="flex items-center gap-2 mb-2">
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-[#E2001A]/10 text-[#E2001A] text-[10px] font-bold">
                  {i + 1}
                </div>
                <step.icon className="h-3.5 w-3.5 text-zinc-500" />
              </div>
              <p className="text-[12px] font-medium text-zinc-200">{step.label}</p>
              <p className="text-[11px] text-zinc-600 mt-1 leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>

        {/* Command to run */}
        <div className="mt-4 rounded-lg bg-[#0f0f0f] border border-[#2a2a2a] px-4 py-3">
          <p className="text-[10px] text-zinc-600 mb-1.5 uppercase tracking-wider">Lancer sur Vast.ai H100</p>
          <code className="text-[12px] text-emerald-400 font-mono">
            bash scripts/run_training.sh
          </code>
          <p className="text-[10px] text-zinc-600 mt-1">Durée estimée : ~25 min · Coût estimé : ~$0.50 GPU + ~$2 OpenAI</p>
        </div>
      </div>

      {/* Quality gate */}
      {bestF1 != null && (
        <div className={`rounded-xl border p-5 ${
          bestF1 >= 0.90 ? "border-emerald-500/30 bg-emerald-500/5"
          : bestF1 >= 0.80 ? "border-amber-500/30 bg-amber-500/5"
          : "border-red-500/30 bg-red-500/5"
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {bestF1 >= 0.80
                ? <CheckCircle2 className={`h-5 w-5 ${bestF1 >= 0.90 ? "text-emerald-400" : "text-amber-400"}`} />
                : <AlertTriangle className="h-5 w-5 text-red-400" />}
              <div>
                <p className="text-sm font-semibold text-white">Meilleur modèle</p>
                <p className="text-[11px] text-zinc-500 mt-0.5">{qualityLabel(bestF1)} · seuil production ≥ 0.80</p>
              </div>
            </div>
            <div className="text-right">
              <p className={`text-3xl font-bold tabular-nums ${qualityColor(bestF1)}`}>
                {(bestF1 * 100).toFixed(1)}%
              </p>
              <p className="text-[10px] text-zinc-600 mt-0.5">F1 macro (test set)</p>
            </div>
          </div>
        </div>
      )}

      {/* MLflow runs */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-white">
            Runs d'entraînement
            {classifierExp && (
              <span className="ml-2 text-[11px] text-zinc-500 font-normal">
                {classifierExp.name}
              </span>
            )}
          </h2>
          {(expLoading || runsLoading) && (
            <div className="flex items-center gap-1.5 text-zinc-600">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span className="text-[11px]">Chargement…</span>
            </div>
          )}
        </div>

        {!expLoading && !classifierExp && (
          <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-8 text-center">
            <Dumbbell className="h-8 w-8 text-zinc-700 mx-auto mb-3" />
            <p className="text-sm text-zinc-500">Aucun run d'entraînement trouvé</p>
            <p className="text-[12px] text-zinc-600 mt-1">
              Lancez <code className="text-zinc-400">bash scripts/run_training.sh</code> sur Vast.ai pour commencer
            </p>
          </div>
        )}

        {runs.length > 0 && (
          <div className="space-y-3">
            {runs.map(run => (
              <RunCard key={run.info.run_id} run={run} />
            ))}
          </div>
        )}
      </div>

      {/* Metrics legend */}
      <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
        <h2 className="text-sm font-semibold text-white mb-3">Seuils de qualité</h2>
        <div className="grid grid-cols-1 gap-4 text-[12px] sm:grid-cols-3">
          <div className="flex items-start gap-2.5">
            <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 shrink-0" />
            <div>
              <p className="text-zinc-200 font-medium">F1 macro ≥ 0.90</p>
              <p className="text-zinc-500">Prêt pour production, déploiement sur Fly.io recommandé</p>
            </div>
          </div>
          <div className="flex items-start gap-2.5">
            <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-amber-400 shrink-0" />
            <div>
              <p className="text-zinc-200 font-medium">F1 macro 0.80–0.90</p>
              <p className="text-zinc-500">Acceptable — surveiller les intentions faibles, envisager plus de données</p>
            </div>
          </div>
          <div className="flex items-start gap-2.5">
            <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-red-400 shrink-0" />
            <div>
              <p className="text-zinc-200 font-medium">F1 macro &lt; 0.80</p>
              <p className="text-zinc-500">Insuffisant — augmenter les données ou ajuster les hyperparamètres</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
