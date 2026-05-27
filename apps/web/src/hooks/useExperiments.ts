"use client"

import useSWR from "swr"
import { api, type MLflowExperiment, type MLflowRun } from "@/lib/api"

export function useExperiments() {
  return useSWR<{ experiments: MLflowExperiment[] }>("experiments", api.experiments.list, {
    refreshInterval: 30_000,
  })
}

export function useExperimentRuns(experimentId: string | null) {
  return useSWR<{ runs: MLflowRun[] }>(
    experimentId ? `experiments/${experimentId}/runs` : null,
    experimentId ? () => api.experiments.runs(experimentId) : null,
    { refreshInterval: 15_000 }
  )
}
