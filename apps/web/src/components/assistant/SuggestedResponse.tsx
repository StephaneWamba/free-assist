"use client"

import { useState } from "react"
import { Copy, Check, FileText, ThumbsUp, ThumbsDown } from "lucide-react"

interface SuggestedResponseProps {
  response: string
  sources: string[]
}

export function SuggestedResponse({ response, sources }: SuggestedResponseProps) {
  const [copied, setCopied] = useState(false)
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(response)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-xl border border-[#E2001A]/20 bg-[#141414] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1e1e1e] bg-[#E2001A]/5">
        <p className="text-[11px] font-semibold text-[#E2001A] uppercase tracking-widest">
          Réponse suggérée par l'IA
        </p>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-colors"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copié" : "Copier"}
        </button>
      </div>

      {/* Response body */}
      <div className="px-5 py-4">
        <p className="text-[14px] text-zinc-200 leading-relaxed whitespace-pre-wrap">{response}</p>
      </div>

      {/* Sources */}
      {sources.length > 0 && (
        <div className="px-5 pb-4">
          <p className="text-[10px] font-medium text-zinc-600 uppercase tracking-widest mb-2">
            Sources RAG
          </p>
          <div className="flex flex-wrap gap-2">
            {sources.map((src) => (
              <span
                key={src}
                className="inline-flex items-center gap-1 rounded-md bg-white/5 px-2 py-1 text-[11px] text-zinc-500"
              >
                <FileText className="h-3 w-3" />
                {src.split("/").pop()}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Feedback */}
      <div className="flex items-center justify-between px-5 py-3 border-t border-[#1e1e1e]">
        <p className="text-[11px] text-zinc-600">Cette suggestion est-elle utile ?</p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setFeedback("up")}
            className={`rounded-md p-1.5 transition-colors ${
              feedback === "up"
                ? "bg-emerald-500/10 text-emerald-400"
                : "text-zinc-600 hover:text-zinc-300 hover:bg-white/5"
            }`}
          >
            <ThumbsUp className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setFeedback("down")}
            className={`rounded-md p-1.5 transition-colors ${
              feedback === "down"
                ? "bg-red-500/10 text-red-400"
                : "text-zinc-600 hover:text-zinc-300 hover:bg-white/5"
            }`}
          >
            <ThumbsDown className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
}
