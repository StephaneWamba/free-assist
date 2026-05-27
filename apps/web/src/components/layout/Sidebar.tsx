"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  MessageSquareText,
  FlaskConical,
  BrainCircuit,
  BookOpen,
  BarChart3,
  Activity,
  Dumbbell,
  Sun,
  Moon,
} from "lucide-react"
import { cn } from "@/lib/utils"
import Image from "next/image"
import { useTheme } from "./ThemeProvider"
import useSWR from "swr"
import { api } from "@/lib/api"

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/assistant", label: "Assistant Live", icon: MessageSquareText },
  { href: "/experiments", label: "Expériences ML", icon: FlaskConical },
  { href: "/models", label: "Modèles", icon: BrainCircuit },
  { href: "/knowledge-base", label: "Base de connaissances", icon: BookOpen },
  { href: "/evaluation", label: "Évaluation", icon: BarChart3 },
  { href: "/monitoring", label: "Monitoring", icon: Activity },
  { href: "/training", label: "Entraînement", icon: Dumbbell },
]

function OpenAIBadge() {
  const { data, error } = useSWR("health", api.health, { refreshInterval: 60_000 })

  const status = error ? "error" : data?.openai_status

  const color =
    status === "ok" ? "bg-emerald-500" :
    status === "error" ? "bg-red-500" :
    status === "no_key" ? "bg-zinc-500" :
    "bg-zinc-700"

  const label =
    status === "ok" ? "OpenAI OK" :
    status === "error" ? "OpenAI KO" :
    status === "no_key" ? "OpenAI non configuré" :
    "OpenAI inconnu"

  return (
    <div className="flex items-center gap-1.5 mt-1.5">
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${color}`} />
      <p className="text-[10px] text-zinc-500">{label}</p>
    </div>
  )
}

interface SidebarProps {
  open?: boolean
  onClose?: () => void
}

export function Sidebar({ open = false, onClose }: SidebarProps) {
  const pathname = usePathname()
  const { theme, toggle } = useTheme()

  return (
    <aside className={`fixed left-0 top-0 h-screen w-60 bg-white dark:bg-[#0f0f0f] border-r border-zinc-200 dark:border-[#1e1e1e] flex flex-col z-40 transition-transform duration-200 ${open ? "translate-x-0" : "-translate-x-full"} md:translate-x-0`}>
      {/* Header - logo Free + nom du produit */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-zinc-200 dark:border-[#1e1e1e]">
        <Image src="/logo.png" alt="Free" width={52} height={32} className="object-contain" />
        <div>
          <p className="text-[13px] font-semibold text-zinc-900 dark:text-white leading-none tracking-tight">
            FreeAssist
          </p>
          <p className="text-[10px] text-zinc-500 mt-1 font-medium uppercase tracking-widest">
            dataX - Support IA
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        <p className="px-3 mb-2 text-[10px] font-semibold text-zinc-400 dark:text-zinc-600 uppercase tracking-widest">
          Plateforme
        </p>
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href))
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-[13px] transition-colors duration-150",
                active
                  ? "bg-[#E2001A]/10 text-[#E2001A] font-medium border-r-2 border-[#E2001A]"
                  : "text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-zinc-100"
              )}
            >
              <Icon className="h-[15px] w-[15px] shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-zinc-200 dark:border-[#1e1e1e]">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <p className="text-[10px] text-zinc-500">Production - v0.1.0</p>
            </div>
            <OpenAIBadge />
          </div>
          <button
            onClick={toggle}
            className="rounded-md p-1.5 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-white/5 transition-colors"
            title={theme === "dark" ? "Passer en mode clair" : "Passer en mode sombre"}
          >
            {theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>
    </aside>
  )
}
