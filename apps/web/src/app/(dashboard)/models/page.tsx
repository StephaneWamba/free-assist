"use client"

import { AppShell } from "@/components/layout/AppShell"
import { ModelsView } from "@/components/models/ModelsView"

export default function ModelsPage() {
  return (
    <AppShell
      title="Modèles"
      subtitle="Catalogue des modèles ML · Statut d'inférence · CamemBERT · Mistral-7B"
    >
      <ModelsView />
    </AppShell>
  )
}
