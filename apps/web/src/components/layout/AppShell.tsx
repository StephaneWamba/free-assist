"use client"

import { useState } from "react"
import { Menu } from "lucide-react"
import { Sidebar } from "./Sidebar"

interface AppShellProps {
  children: React.ReactNode
  title?: string
  subtitle?: string
}

export function AppShell({ children, title, subtitle }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-white dark:bg-[#0a0a0a] text-zinc-900 dark:text-zinc-100 font-sans antialiased">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <main className="md:ml-60 min-h-screen">
        {/* Mobile top bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-200 dark:border-[#1e1e1e] bg-zinc-50 dark:bg-[#0f0f0f] md:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-1.5 text-zinc-500 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-white/5 transition-colors"
          >
            <Menu className="h-5 w-5" />
          </button>
          {title && (
            <h1 className="text-sm font-semibold text-zinc-900 dark:text-white tracking-tight truncate">
              {title}
            </h1>
          )}
        </div>

        {(title || subtitle) && (
          <header className="hidden md:block border-b border-zinc-200 dark:border-[#1e1e1e] bg-zinc-50 dark:bg-[#0f0f0f] px-8 py-5">
            {title && (
              <h1 className="text-lg font-semibold text-zinc-900 dark:text-white tracking-tight">{title}</h1>
            )}
            {subtitle && <p className="mt-0.5 text-sm text-zinc-500">{subtitle}</p>}
          </header>
        )}

        <div className="px-4 py-5 md:px-8 md:py-7">{children}</div>
      </main>
    </div>
  )
}
