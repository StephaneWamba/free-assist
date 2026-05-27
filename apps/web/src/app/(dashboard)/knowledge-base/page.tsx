"use client"

import { AppShell } from "@/components/layout/AppShell"
import { KnowledgeBaseView } from "@/components/knowledge-base/KnowledgeBaseView"

export default function KnowledgeBasePage() {
  return (
    <AppShell
      title="Base de connaissances"
      subtitle="Procédures Free · FAQ · Documents source pour le RAG"
    >
      <KnowledgeBaseView />
    </AppShell>
  )
}
