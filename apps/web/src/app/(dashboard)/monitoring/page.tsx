import { AppShell } from "@/components/layout/AppShell"
import { MonitoringView } from "@/components/monitoring/MonitoringView"

export default function MonitoringPage() {
  return (
    <AppShell title="Monitoring" subtitle="Data drift · Dérive des intentions · Performance en production">
      <MonitoringView />
    </AppShell>
  )
}
