"use client"

import useSWR from "swr"
import { api, type MonitoringAlert, type DriftPoint } from "@/lib/api"

export function useMonitoringAlerts() {
  return useSWR<MonitoringAlert[]>("monitoring/alerts", api.monitoring.alerts, {
    refreshInterval: 30_000,
  })
}

export function useDriftData(topIntents = 3) {
  return useSWR<DriftPoint[]>(`monitoring/drift/${topIntents}`, () => api.monitoring.drift(topIntents), {
    refreshInterval: 60_000,
  })
}
