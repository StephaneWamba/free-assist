"use client"

import { AppShell } from "@/components/layout/AppShell"
import { TrainingView } from "@/components/training/TrainingView"

export default function TrainingPage() {
  return (
    <AppShell
      title="Entraînement"
      subtitle="CamemBERT fine-tuning · Données synthétiques · Métriques MLflow"
    >
      <TrainingView />
    </AppShell>
  )
}
