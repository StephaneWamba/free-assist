interface ConfidenceBarProps {
  value: number // 0–1
}

export function ConfidenceBar({ value }: ConfidenceBarProps) {
  const pct = Math.round(value * 100)
  const color = pct >= 90 ? "#10b981" : pct >= 75 ? "#f59e0b" : "#E2001A"

  return (
    <div className="space-y-1.5">
      <div className="h-1.5 w-full rounded-full bg-white/5">
        <div
          className="h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-zinc-600">
        <span>Incertain</span>
        <span>Très confiant</span>
      </div>
    </div>
  )
}
