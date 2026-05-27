"use client"

import { INTENT_LABELS, INTENT_COLORS, type IntentScores } from "@/types/assistant"

interface ScoreBreakdownProps {
  scores: IntentScores
}

export function ScoreBreakdown({ scores }: ScoreBreakdownProps) {
  const sorted = Object.entries(scores).sort(([, a], [, b]) => b - a)

  return (
    <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
      <p className="text-[11px] font-medium text-zinc-500 uppercase tracking-widest mb-4">
        Scores par intention
      </p>
      <div className="space-y-2.5">
        {sorted.map(([intent, score]) => {
          const pct = Math.round(score * 100)
          const color = INTENT_COLORS[intent] ?? "#6b7280"
          return (
            <div key={intent} className="flex items-center gap-3">
              <span className="w-36 shrink-0 text-[11px] text-zinc-400 truncate">
                {INTENT_LABELS[intent] ?? intent}
              </span>
              <div className="flex-1 h-1.5 rounded-full bg-white/5">
                <div
                  className="h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${pct}%`, backgroundColor: color, opacity: pct > 5 ? 1 : 0.3 }}
                />
              </div>
              <span className="w-10 text-right text-[11px] font-mono text-zinc-500 tabular-nums">
                {pct}%
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
