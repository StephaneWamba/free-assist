import { AppShell } from "@/components/layout/AppShell"
import { ExperimentsView } from "@/components/experiments/ExperimentsView"

export default function ExperimentsPage() {
  return (
    <AppShell
      title="Expériences ML"
      subtitle="Suivi des entraînements · MLflow · Comparaison de runs"
    >
      <ExperimentsView />
    </AppShell>
  )
}
