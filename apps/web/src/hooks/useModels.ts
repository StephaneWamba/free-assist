import useSWR from "swr"
import { api } from "@/lib/api"

export function useModels() {
  return useSWR("models", () => api.models.list(), { refreshInterval: 30_000 })
}
