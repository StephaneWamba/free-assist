import useSWR from "swr"
import { api } from "@/lib/api"

export function useKnowledgeDocs(category?: string, q?: string) {
  const key = `kb-${category ?? ""}-${q ?? ""}`
  return useSWR(key, () => api.knowledgeBase.list(category, q), { revalidateOnFocus: false })
}

export function useKnowledgeDoc(id: string | null) {
  return useSWR(id ? `kb-doc-${id}` : null, () => api.knowledgeBase.get(id!), {
    revalidateOnFocus: false,
  })
}
