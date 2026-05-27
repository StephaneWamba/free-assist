"use client"

import { AppShell } from "@/components/layout/AppShell"
import { EvaluationView } from "@/components/evaluation/EvaluationView"

export default function EvaluationPage() {
  return (
    <AppShell
      title="Évaluation"
      subtitle="LLM-as-judge · Métriques de qualité · Historique MLflow"
    >
      <EvaluationView />
    </AppShell>
  )
}
