"use client"

import useSWR from "swr"
import { api, type DashboardKPIs, type IntentBucket, type RecentTicket } from "@/lib/api"

export function useDashboardKPIs() {
  return useSWR<DashboardKPIs>("stats/kpis", api.stats.kpis, {
    refreshInterval: 30_000,
  })
}

export function useRecentTickets(limit = 10) {
  return useSWR<RecentTicket[]>(`stats/recent/${limit}`, () => api.stats.recent(limit), {
    refreshInterval: 15_000,
  })
}

export function useIntentDistribution() {
  return useSWR<IntentBucket[]>("stats/intent-distribution", api.stats.intentDistribution, {
    refreshInterval: 30_000,
  })
}
