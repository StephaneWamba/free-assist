"use client"

import { useId, useState } from "react"
import { useAssistant } from "@/hooks/useAssistant"
import { IntentBadge } from "./IntentBadge"
import { ConfidenceBar } from "./ConfidenceBar"
import { SuggestedResponse } from "./SuggestedResponse"
import { ScoreBreakdown } from "./ScoreBreakdown"
import { Loader2, Send, RotateCcw } from "lucide-react"
import Image from "next/image"
import { cn, formatMs } from "@/lib/utils"

const EXAMPLE_TICKETS = [
  "Ma box free ne se connecte plus depuis ce matin, les voyants sont rouge fixe",
  "J'ai été prélevé deux fois ce mois-ci, je veux un remboursement immédiat",
  "Comment je fais pour garder mon numéro de portable en venant chez free ?",
  "Mon débit fibre est à 8 Mbps alors que j'ai souscrit au giga, ça fait 3 jours",
]

export function AssistantWorkspace() {
  const conversationId = useId()
  const { result, status, error, analyze, reset } = useAssistant(conversationId)
  const [inputValue, setInputValue] = useState("")

  const handleSubmit = () => {
    if (!inputValue.trim()) return
    analyze(inputValue)
  }

  const handleExample = (text: string) => {
    setInputValue(text)
    analyze(text)
  }

  const isLoading = status === "analyzing" || status === "connecting"

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2 lg:h-[calc(100vh-12rem)]">
      {/* Left — Ticket input */}
      <div className="flex flex-col gap-4">
        <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] flex flex-col flex-1 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1e1e1e]">
            <div>
              <h2 className="text-[13px] font-semibold text-white">Ticket client</h2>
              <p className="text-[11px] text-zinc-500 mt-0.5">Message brut reçu par le support</p>
            </div>
            <button
              onClick={() => { reset(); setInputValue("") }}
              className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Réinitialiser
            </button>
          </div>

          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Saisissez ou collez un message client ici…"
            className="flex-1 resize-none bg-transparent px-5 py-4 text-[14px] text-zinc-200 placeholder:text-zinc-600 outline-none leading-relaxed"
          />

          <div className="flex items-center justify-between px-5 py-3 border-t border-[#1e1e1e]">
            <span className="text-[11px] text-zinc-600">{inputValue.length} caractères</span>
            <button
              onClick={handleSubmit}
              disabled={!inputValue.trim() || isLoading}
              className={cn(
                "flex items-center gap-2 rounded-lg px-4 py-2 text-[13px] font-medium transition-colors",
                "bg-[#E2001A] text-white hover:bg-[#c40017]",
                "disabled:opacity-40 disabled:cursor-not-allowed"
              )}
            >
              {isLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
              Analyser
            </button>
          </div>
        </div>

        {/* Example tickets */}
        <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-4">
          <p className="text-[11px] font-medium text-zinc-500 uppercase tracking-widest mb-3">
            Exemples de tickets
          </p>
          <div className="space-y-2">
            {EXAMPLE_TICKETS.map((t) => (
              <button
                key={t}
                onClick={() => handleExample(t)}
                className="w-full text-left rounded-lg border border-[#1e1e1e] bg-[#1a1a1a] px-3 py-2.5 text-[12px] text-zinc-400 hover:text-zinc-200 hover:border-[#2a2a2a] transition-colors leading-snug"
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Right — Analysis results */}
      <div className="flex flex-col gap-4 overflow-y-auto min-h-0">
        {error && (
          <div className="rounded-xl border border-red-900/40 bg-red-950/20 px-5 py-4 text-[13px] text-red-400">
            {error}
          </div>
        )}

        {!result && !isLoading && (
          <div className="flex-1 flex items-center justify-center rounded-xl border border-[#1e1e1e] bg-[#141414]">
            <div className="text-center">
              <Image
                src="/logo.png"
                alt="FreeAssist"
                width={120}
                height={72}
                className="object-contain mx-auto mb-4 opacity-80"
              />
              <p className="text-sm font-medium text-zinc-400">Prête à analyser</p>
              <p className="text-xs text-zinc-600 mt-1">Saisissez un ticket pour démarrer</p>
            </div>
          </div>
        )}

        {isLoading && !result && (
          <div className="flex-1 flex items-center justify-center rounded-xl border border-[#1e1e1e] bg-[#141414]">
            <div className="text-center">
              <Loader2 className="h-7 w-7 text-[#E2001A] mx-auto mb-3 animate-spin" />
              <p className="text-sm text-zinc-400">Analyse en cours…</p>
            </div>
          </div>
        )}

        {result && (
          <>
            {/* Intent + confidence */}
            <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <p className="text-[11px] font-medium text-zinc-500 uppercase tracking-widest mb-2">
                    Intention détectée
                  </p>
                  <IntentBadge intent={result.intent} size="lg" />
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[11px] text-zinc-500 mb-1">Confiance</p>
                  <p className="text-2xl font-bold text-white tabular-nums">
                    {(result.confidence * 100).toFixed(1)}%
                  </p>
                  <p className="text-[11px] text-zinc-600 font-mono mt-0.5">
                    {formatMs(result.processing_ms)}
                  </p>
                </div>
              </div>
              <ConfidenceBar value={result.confidence} />
            </div>

            {/* Score breakdown */}
            <ScoreBreakdown scores={result.all_scores} />

            {/* Summary (if available) */}
            {result.summary && (
              <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
                <p className="text-[11px] font-medium text-zinc-500 uppercase tracking-widest mb-2">
                  Résumé automatique
                </p>
                <p className="text-[13px] text-zinc-300 leading-relaxed">{result.summary}</p>
              </div>
            )}

            {/* Suggested response */}
            <SuggestedResponse
              response={result.suggested_response}
              sources={result.source_documents}
            />
          </>
        )}
      </div>
    </div>
  )
}
