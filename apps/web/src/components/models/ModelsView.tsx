"use client"

import { Cpu, Brain, Database, Zap, AlertCircle, Loader2 } from "lucide-react"
import { useModels } from "@/hooks/useModels"
import type { ModelInfo } from "@/lib/api"

const TYPE_ICON = {
  classifier: Brain,
  llm: Zap,
  embeddings: Database,
}

type StatusStyle = { dot: string; label: string; badge: string }

const STATUS_STYLES = {
  active:     { dot: "bg-emerald-400",              label: "Actif",        badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  loading:    { dot: "bg-amber-400 animate-pulse",  label: "Chargement…",  badge: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  standby:    { dot: "bg-zinc-500",                 label: "Standby",      badge: "bg-zinc-800 text-zinc-400 border-zinc-700" },
  not_loaded: { dot: "bg-zinc-700",                 label: "Non chargé",   badge: "bg-zinc-900 text-zinc-600 border-zinc-800" },
} as const satisfies Record<string, StatusStyle>

const FALLBACK_STATUS: StatusStyle = STATUS_STYLES.not_loaded

type ModeLabel = { label: string; color: string }

const MODE_LABELS = {
  local:  { label: "Modèles locaux (GPU)",          color: "text-emerald-400" },
  openai: { label: "OpenAI fallback (gpt-4o-mini)", color: "text-amber-400" },
  none:   { label: "Non initialisé",                color: "text-red-400" },
} as const satisfies Record<string, ModeLabel>

const FALLBACK_MODE: ModeLabel = MODE_LABELS.none

function ModelCard({ model }: { model: ModelInfo }) {
  const Icon = TYPE_ICON[model.type as keyof typeof TYPE_ICON] ?? Brain
  const s: StatusStyle = STATUS_STYLES[model.status as keyof typeof STATUS_STYLES] ?? FALLBACK_STATUS

  return (
    <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#1e1e1e]">
            <Icon className="h-4 w-4 text-zinc-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white leading-tight">{model.name}</p>
            <p className="text-[11px] text-zinc-500 mt-0.5">{model.task}</p>
          </div>
        </div>
        <span className={`flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${s.badge}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
          {s.label}
        </span>
      </div>

      <p className="text-[12px] text-zinc-400 leading-relaxed">{model.description}</p>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
        <span className="text-zinc-600">Modèle de base</span>
        <span className="text-zinc-300 font-mono truncate">{model.base_model}</span>

        {model.params_m != null && (
          <>
            <span className="text-zinc-600">Paramètres</span>
            <span className="text-zinc-300">{model.params_m.toLocaleString("fr-FR")}M</span>
          </>
        )}

        <span className="text-zinc-600">Langue</span>
        <span className="text-zinc-300">{model.language}</span>

        {model.device && (
          <>
            <span className="text-zinc-600">Device</span>
            <span className="text-zinc-300 flex items-center gap-1">
              <Cpu className="h-3 w-3" />
              {model.device.toUpperCase()}
            </span>
          </>
        )}

        {model.hf_id && (
          <>
            <span className="text-zinc-600">HuggingFace</span>
            <span className="text-zinc-400 font-mono text-[10px] truncate">{model.hf_id}</span>
          </>
        )}
      </div>
    </div>
  )
}

export function ModelsView() {
  const { data, isLoading, error } = useModels()

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center gap-2 text-zinc-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Chargement…</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex h-64 items-center justify-center gap-2 text-red-400">
        <AlertCircle className="h-4 w-4" />
        <span className="text-sm">Impossible de charger les modèles</span>
      </div>
    )
  }

  const mode: ModeLabel = MODE_LABELS[data.ml_mode as keyof typeof MODE_LABELS] ?? FALLBACK_MODE
  const activeModels = data.models.filter(m => m.status === "active")
  const localModels = data.models.filter(m => m.hf_id !== null)
  const fallbackModels = data.models.filter(m => m.hf_id === null)

  return (
    <div className="space-y-6">
      {/* Status banner */}
      <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <p className="text-xs text-zinc-500 mb-1">Mode d'inférence actuel</p>
            <p className={`text-lg font-semibold ${mode.color}`}>{mode.label}</p>
          </div>
          <div className="flex gap-6 text-center">
            <div>
              <p className="text-2xl font-bold text-white">{activeModels.length}</p>
              <p className="text-xs text-zinc-500 mt-0.5">actifs</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-zinc-400">{data.models.length}</p>
              <p className="text-xs text-zinc-500 mt-0.5">total</p>
            </div>
            <div>
              <p className="text-lg font-bold text-zinc-300 uppercase">{data.device}</p>
              <p className="text-xs text-zinc-500 mt-0.5">device</p>
            </div>
          </div>
        </div>
      </div>

      {/* Local models */}
      <div>
        <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
          Modèles locaux (GPU)
        </h2>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {localModels.map(m => <ModelCard key={m.id} model={m} />)}
        </div>
      </div>

      {/* Fallback models */}
      <div>
        <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
          Fallback OpenAI
        </h2>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {fallbackModels.map(m => <ModelCard key={m.id} model={m} />)}
        </div>
      </div>
    </div>
  )
}
