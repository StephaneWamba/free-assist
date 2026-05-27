import { AppShell } from "@/components/layout/AppShell"
import { AssistantWorkspace } from "@/components/assistant/AssistantWorkspace"

export default function AssistantPage() {
  return (
    <AppShell
      title="Assistant Live"
      subtitle="Analyse en temps réel des tickets client · Classification · RAG · Résumé"
    >
      <AssistantWorkspace />
    </AppShell>
  )
}
