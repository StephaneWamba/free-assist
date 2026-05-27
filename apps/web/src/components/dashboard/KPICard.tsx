import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface KPICardProps {
  label: string
  value: string | number
  subtitle?: string
  icon: LucideIcon
  trend?: { value: number; label: string }
  variant?: "default" | "success" | "warning" | "danger"
}

const ICON_VARIANTS = {
  default: "text-zinc-400 bg-white/5",
  success: "text-emerald-400 bg-emerald-500/10",
  warning: "text-amber-400 bg-amber-500/10",
  danger: "text-[#E2001A] bg-[#E2001A]/10",
}

export function KPICard({ label, value, subtitle, icon: Icon, trend, variant = "default" }: KPICardProps) {
  return (
    <div className="rounded-xl border border-[#1e1e1e] bg-[#141414] p-5 hover:border-[#2a2a2a] transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[11px] font-medium text-zinc-500 uppercase tracking-widest truncate">
            {label}
          </p>
          <p className="mt-2 text-[28px] font-bold text-white leading-none tabular-nums">
            {value}
          </p>
          {subtitle && (
            <p className="mt-1.5 text-[12px] text-zinc-500 truncate">{subtitle}</p>
          )}
          {trend && (
            <p className={cn(
              "mt-2 text-[12px] font-medium",
              trend.value >= 0 ? "text-emerald-400" : "text-red-400"
            )}>
              {trend.value >= 0 ? "▲" : "▼"} {Math.abs(trend.value)}% {trend.label}
            </p>
          )}
        </div>
        <div className={cn("shrink-0 rounded-lg p-2.5", ICON_VARIANTS[variant])}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  )
}
