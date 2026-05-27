const BENCHMARKS = [
  { model: "Zero-shot GPT-4", accuracy: 0.710, f1_macro: 0.678, latency_ms: 1200, notes: "Baseline" },
  { model: "CamemBERT (base)", accuracy: 0.840, f1_macro: 0.821, latency_ms: 45, notes: "Pré-entraîné" },
  { model: "CamemBERT fine-tuned", accuracy: 0.931, f1_macro: 0.914, latency_ms: 45, notes: "Production" },
  { model: "RAG + Mistral-7B", accuracy: 0.892, f1_macro: 0.871, latency_ms: 380, notes: "RAG seul" },
  { model: "QLoRA Mistral-7B", accuracy: 0.943, f1_macro: 0.931, latency_ms: 210, notes: "Fine-tuned" },
]

function Score({ value }: { value: number }) {
  const color =
    value >= 0.92 ? "text-emerald-400" :
    value >= 0.85 ? "text-amber-400" :
    "text-zinc-400"
  return <span className={`font-mono font-semibold ${color}`}>{value.toFixed(3)}</span>
}

function Badge({ label }: { label: string }) {
  const isProduction = label === "Production"
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
      isProduction
        ? "bg-[#E2001A]/10 text-[#E2001A] ring-1 ring-[#E2001A]/20"
        : "bg-zinc-800 text-zinc-400"
    }`}>
      {label}
    </span>
  )
}

export function ModelBenchmarkTable() {
  return (
    <div className="rounded-xl border border-[#1e1e1e] bg-[#141414]">
      <div className="px-5 py-4 border-b border-[#1e1e1e]">
        <h2 className="text-sm font-semibold text-white">Comparatif modèles</h2>
        <p className="mt-0.5 text-xs text-zinc-500">Classification d'intention · jeu de test (n=400)</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1e1e1e]">
              {["Modèle", "Accuracy", "F1 Macro", "Latence", ""].map((h) => (
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
            {BENCHMARKS.map((row) => (
              <tr key={row.model} className="hover:bg-white/[0.02] transition-colors">
                <td className="px-5 py-3.5 text-[13px] font-medium text-zinc-200">{row.model}</td>
                <td className="px-5 py-3.5"><Score value={row.accuracy} /></td>
                <td className="px-5 py-3.5"><Score value={row.f1_macro} /></td>
                <td className="px-5 py-3.5 font-mono text-[13px] text-zinc-400">{row.latency_ms}ms</td>
                <td className="px-5 py-3.5"><Badge label={row.notes} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
