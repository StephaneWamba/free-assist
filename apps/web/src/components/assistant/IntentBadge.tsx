import { cn } from "@/lib/utils"
import { INTENT_LABELS, INTENT_COLORS } from "@/types/assistant"

interface IntentBadgeProps {
  intent: string
  size?: "sm" | "md" | "lg"
}

export function IntentBadge({ intent, size = "md" }: IntentBadgeProps) {
  const color = INTENT_COLORS[intent] ?? "#6b7280"
  const label = INTENT_LABELS[intent] ?? intent

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium",
        size === "sm" && "px-2 py-0.5 text-[11px]",
        size === "md" && "px-2.5 py-1 text-[12px]",
        size === "lg" && "px-3.5 py-1.5 text-[14px]",
      )}
      style={{
        backgroundColor: `${color}18`,
        color,
        boxShadow: `inset 0 0 0 1px ${color}30`,
      }}
    >
      <span
        className="inline-block rounded-full shrink-0"
        style={{ backgroundColor: color, width: size === "lg" ? 7 : 5, height: size === "lg" ? 7 : 5 }}
      />
      {label}
    </span>
  )
}
