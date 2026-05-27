"use client"

import { INTENT_LABELS, INTENT_COLORS } from "@/types/assistant"
import { useRecentTickets } from "@/hooks/useDashboardStats"

export function RecentTicketsFeed() {
  const { data: tickets, isLoading } = useRecentTickets(10)

  return (
    <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] h-full">
      <div className="px-5 py-4 border-b border-[#1e1e1e]">
        <h2 className="text-sm font-semibold text-white">Tickets récents</h2>
        <p className="mt-0.5 text-xs text-zinc-500">Analyse en temps réel</p>
      </div>

      {isLoading && (
        <div className="px-5 py-6 text-xs text-zinc-600">Chargement…</div>
      )}

      {!isLoading && (!tickets || tickets.length === 0) && (
        <div className="px-5 py-6 text-xs text-zinc-600">
          Aucun ticket pour le moment
        </div>
      )}

      {tickets && tickets.length > 0 && (
        <ul className="divide-y divide-[#1e1e1e]">
          {tickets.map((ticket) => (
            <li key={ticket.id} className="px-5 py-3.5 hover:bg-white/[0.02] transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[12px] text-zinc-300 truncate leading-snug">
                    {ticket.text_preview}
                  </p>
                  <div className="mt-1.5 flex items-center gap-2">
                    <span
                      className="inline-block h-1.5 w-1.5 rounded-full shrink-0"
                      style={{
                        backgroundColor: INTENT_COLORS[ticket.intent] ?? "#71717a",
                      }}
                    />
                    <span className="text-[11px] text-zinc-500">
                      {INTENT_LABELS[ticket.intent] ?? ticket.intent}
                    </span>
                    <span className="text-[11px] text-zinc-600">·</span>
                    <span className="text-[11px] text-zinc-600 font-mono">
                      {ticket.processing_ms}ms
                    </span>
                  </div>
                </div>
                <span className="shrink-0 text-[11px] font-mono text-zinc-600">
                  #{ticket.id}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
