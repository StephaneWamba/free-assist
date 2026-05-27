export interface IntentScores {
  BOX_CONNECTIVITY: number
  BOX_REBOOT: number
  MOBILE_PORTABILITY: number
  BILLING_DISPUTE: number
  CONTRACT_CHANGE: number
  TECHNICAL_OUTAGE: number
  EQUIPMENT_RETURN: number
  SPEED_ISSUE: number
  CANCELLATION: number
  OTHER: number
}

export interface AnalysisResult {
  intent: string
  confidence: number
  all_scores: IntentScores
  suggested_response: string
  source_documents: string[]
  summary: string | null
  processing_ms: number
  cleaned_input: string
}

export interface ConversationTurn {
  role: "user" | "agent"
  content: string
  timestamp: string
  analysis?: AnalysisResult
}

export const INTENT_LABELS: Record<string, string> = {
  BOX_CONNECTIVITY: "Connexion box",
  BOX_REBOOT: "Redémarrage box",
  MOBILE_PORTABILITY: "Portabilité mobile",
  BILLING_DISPUTE: "Litige facturation",
  CONTRACT_CHANGE: "Changement d'offre",
  TECHNICAL_OUTAGE: "Panne technique",
  EQUIPMENT_RETURN: "Retour matériel",
  SPEED_ISSUE: "Problème de débit",
  CANCELLATION: "Résiliation",
  OTHER: "Autre",
}

export const INTENT_COLORS: Record<string, string> = {
  BOX_CONNECTIVITY: "#3b82f6",
  BOX_REBOOT: "#8b5cf6",
  MOBILE_PORTABILITY: "#06b6d4",
  BILLING_DISPUTE: "#ef4444",
  CONTRACT_CHANGE: "#f59e0b",
  TECHNICAL_OUTAGE: "#f97316",
  EQUIPMENT_RETURN: "#10b981",
  SPEED_ISSUE: "#6366f1",
  CANCELLATION: "#ec4899",
  OTHER: "#6b7280",
}
