"use client"

import { useState } from "react"
import { Send, CheckCircle2, AlertTriangle, Loader2, FlaskConical, ThumbsUp, ThumbsDown } from "lucide-react"
import { api } from "@/lib/api"
import type { EvalScores } from "@/lib/api"
import { useExperiments, useExperimentRuns } from "@/hooks/useExperiments"
import { IntentBadge } from "@/components/assistant/IntentBadge"
import { ConfidenceBar } from "@/components/assistant/ConfidenceBar"
import type { AnalysisResult } from "@/types/assistant"

const EVAL_EXAMPLES = [
  "Ma Freebox ne se connecte plus à internet depuis hier soir, toutes les lumières sont éteintes.",
  "J'ai reçu une facture de 89€ au lieu de mes 49€ habituels, personne ne m'a prévenu.",
  "Je veux résilier mon abonnement Freebox, comment faire et quel est le préavis ?",
  "Mon débit est très lent depuis une semaine, à peine 5 Mbps au lieu des 500 annoncés.",
]

const JUDGE_CRITERIA = [
  { key: "pertinence",  label: "Pertinence",  desc: "La réponse répond-elle au problème ?" },
  { key: "empathie",    label: "Empathie",    desc: "Ton professionnel et empathique ?" },
  { key: "exactitude",  label: "Exactitude",  desc: "Informations correctes et vérifiables ?" },
  { key: "actionnable", label: "Actionnable", desc: "Des étapes concrètes pour le conseiller ?" },
]

function ScoreGauge({ score, label }: { score: number; label: string }) {
  const pct = Math.round(score * 100)
  const color = pct >= 80 ? "text-emerald-400" : pct >= 60 ? "text-amber-400" : "text-red-400"
  return (
    <div className="text-center">
      <p className={`text-2xl font-bold ${color}`}>{pct}</p>
      <p className="text-[10px] text-zinc-500 mt-0.5">{label}</p>
    </div>
  )
}

function MLflowRunsTable() {
  const { data: experiments } = useExperiments()
  const firstExp = experiments?.experiments?.[0]
  const { data: runsData, isLoading } = useExperimentRuns(firstExp?.experiment_id ?? "")

  if (!firstExp) return (
    <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">
      MLflow non connecté — aucune expérience
    </div>
  )

  const runs = runsData?.runs ?? []

  return (
    <div className="overflow-x-auto">
      {isLoading ? (
        <div className="flex items-center justify-center h-32 gap-2 text-zinc-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm">Chargement runs…</span>
        </div>
      ) : runs.length === 0 ? (
        <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">
          Aucun run disponible
        </div>
      ) : (
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-[#1e1e1e]">
              {["Run", "Statut", "F1 macro", "Accuracy", "Durée"].map(h => (
                <th key={h} className="pb-2 text-left text-[11px] text-zinc-600 font-medium pr-4">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1a1a1a]">
            {runs.map(run => {
              const f1  = run.data.metrics?.["eval_f1_macro"] ?? run.data.metrics?.["f1_macro"]
              const acc = run.data.metrics?.["eval_accuracy"] ?? run.data.metrics?.["accuracy"]
              const durationMs  = run.info.end_time - run.info.start_time
              const durationMin = Math.round(durationMs / 60000)
              const isFinished  = run.info.status === "FINISHED"
              return (
                <tr key={run.info.run_id} className="hover:bg-[#1a1a1a]">
                  <td className="py-2 pr-4 text-zinc-200 font-medium">{run.info.run_name || run.info.run_id.slice(0, 8)}</td>
                  <td className="py-2 pr-4">
                    <span className={`flex items-center gap-1.5 w-fit ${isFinished ? "text-emerald-400" : "text-amber-400"}`}>
                      {isFinished
                        ? <CheckCircle2 className="h-3 w-3" />
                        : <AlertTriangle className="h-3 w-3" />}
                      {run.info.status}
                    </span>
                  </td>
                  <td className="py-2 pr-4">
                    <span className={f1 != null && f1 >= 0.9 ? "text-emerald-400" : "text-zinc-300"}>
                      {f1 != null ? f1.toFixed(3) : "—"}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-zinc-300">{acc != null ? acc.toFixed(3) : "—"}</td>
                  <td className="py-2 pr-4 text-zinc-500">{durationMin > 0 ? `${durationMin}min` : "—"}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}

export function EvaluationView() {
  const [text, setText]       = useState("")
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [scores, setScores]   = useState<EvalScores | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null)

  async function evaluate() {
    if (!text.trim() || loading) return
    setLoading(true)
    setError(null)
    setAnalysis(null)
    setScores(null)
    setFeedback(null)

    try {
      // Step 1: classify intent + generate suggested response
      const analysisResult = await api.assistant.analyze(text)
      setAnalysis(analysisResult)

      // Step 2: judge the generated response with gpt-4o-mini
      const judgeScores = await api.evaluation.judge(
        text,
        analysisResult.intent,
        analysisResult.suggested_response,
      )
      setScores(judgeScores)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur d'évaluation")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* Live evaluation panel */}
      <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
        <div className="flex items-center gap-2 mb-4">
          <FlaskConical className="h-4 w-4 text-zinc-500" />
          <h2 className="text-sm font-semibold text-white">Évaluation LLM-as-judge</h2>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Input */}
          <div className="space-y-3">
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              placeholder="Collez un ticket client à évaluer…"
              rows={5}
              className="w-full rounded-lg border border-[#2a2a2a] bg-[#1a1a1a] px-3 py-2.5 text-[13px] text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 resize-none"
            />
            <div className="flex flex-wrap gap-1.5">
              {EVAL_EXAMPLES.map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setText(ex)}
                  className="rounded px-2 py-1 text-[11px] bg-[#1e1e1e] text-zinc-400 hover:text-zinc-200 hover:bg-[#252525] transition-colors text-left max-w-[180px] truncate"
                >
                  {ex.slice(0, 40)}…
                </button>
              ))}
            </div>
            <button
              onClick={evaluate}
              disabled={loading || !text.trim()}
              className="flex items-center gap-2 rounded-lg bg-[#E2001A] px-4 py-2 text-sm font-medium text-white hover:bg-[#c00015] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Évaluer
            </button>
            {error && <p className="text-[12px] text-red-400">{error}</p>}
          </div>

          {/* Results */}
          <div className="space-y-4">
            {!analysis && !loading && (
              <div className="flex h-full items-center justify-center text-zinc-600 text-sm">
                Lancez une évaluation →
              </div>
            )}
            {loading && (
              <div className="flex h-full items-center justify-center gap-2 text-zinc-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">
                  {analysis ? "Évaluation LLM-as-judge…" : "Analyse en cours…"}
                </span>
              </div>
            )}
            {analysis && scores && (
              <div className="space-y-4">
                {/* Intent + confidence */}
                <div className="flex items-center gap-3">
                  <IntentBadge intent={analysis.intent} size="md" />
                  <div className="flex-1">
                    <ConfidenceBar value={analysis.confidence} />
                  </div>
                  <span className="text-[11px] text-zinc-500">{analysis.processing_ms}ms</span>
                </div>

                {/* Judge scores */}
                <div>
                  <p className="text-[11px] text-zinc-500 mb-2">Scores LLM-as-judge</p>
                  <div className="grid grid-cols-4 gap-2 mb-3">
                    {JUDGE_CRITERIA.map(c => (
                      <ScoreGauge key={c.key} score={scores[c.key as keyof EvalScores] as number} label={c.label} />
                    ))}
                  </div>
                  <div className="flex items-center justify-between rounded-lg bg-[#1a1a1a] px-3 py-2">
                    <span className="text-[12px] text-zinc-400">Score global</span>
                    <span className={`text-sm font-bold ${scores.overall >= 0.8 ? "text-emerald-400" : scores.overall >= 0.65 ? "text-amber-400" : "text-red-400"}`}>
                      {Math.round(scores.overall * 100)}/100
                    </span>
                  </div>
                  {scores.justification && (
                    <p className="mt-2 text-[11px] text-zinc-500 italic">{scores.justification}</p>
                  )}
                </div>

                {/* Suggested response preview */}
                <div className="rounded-lg bg-[#1a1a1a] p-3">
                  <p className="text-[11px] text-zinc-500 mb-1.5">Réponse générée</p>
                  <p className="text-[12px] text-zinc-300 leading-relaxed line-clamp-4">
                    {analysis.suggested_response}
                  </p>
                </div>

                {/* Human feedback */}
                <div className="flex items-center gap-3">
                  <p className="text-[11px] text-zinc-500">Votre avis :</p>
                  <button
                    onClick={() => setFeedback("up")}
                    className={`rounded-lg p-1.5 transition-colors ${feedback === "up" ? "bg-emerald-500/20 text-emerald-400" : "text-zinc-600 hover:text-zinc-400"}`}
                  >
                    <ThumbsUp className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => setFeedback("down")}
                    className={`rounded-lg p-1.5 transition-colors ${feedback === "down" ? "bg-red-500/20 text-red-400" : "text-zinc-600 hover:text-zinc-400"}`}
                  >
                    <ThumbsDown className="h-3.5 w-3.5" />
                  </button>
                  {feedback && (
                    <span className="text-[11px] text-zinc-500">
                      {feedback === "up" ? "Bon résultat enregistré" : "Retour négatif enregistré"}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* MLflow runs */}
      <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Historique d'entraînement (MLflow)</h2>
        <MLflowRunsTable />
      </div>
    </div>
  )
}
