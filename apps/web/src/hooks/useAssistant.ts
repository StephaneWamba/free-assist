"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { createAssistantSocket } from "@/lib/ws"
import { api } from "@/lib/api"
import type { AnalysisResult } from "@/types/assistant"

type Status = "idle" | "connecting" | "ready" | "analyzing" | "error"

interface UseAssistantReturn {
  result: AnalysisResult | null
  status: Status
  error: string | null
  analyze: (text: string) => void
  reset: () => void
}

export function useAssistant(conversationId: string): UseAssistantReturn {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [status, setStatus] = useState<Status>("idle")
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    setStatus("connecting")
    wsRef.current = createAssistantSocket(conversationId, {
      onResult: (r) => {
        setResult(r)
        setStatus("ready")
      },
      onError: () => {
        // WS failed — REST fallback will handle; don't block the UI
        setStatus("idle")
      },
      onClose: () => setStatus("idle"),
    })

    return () => {
      wsRef.current?.close()
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [conversationId])

  const analyze = useCallback((text: string) => {
    if (!text.trim() || text.length < 3) return

    // Debounce — wait 400ms after last keystroke before sending
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        setStatus("analyzing")
        wsRef.current.send(JSON.stringify({ text }))
      } else {
        // Fallback to REST if WebSocket not available
        setStatus("analyzing")
        setError(null)
        api.assistant
          .analyze(text, conversationId)
          .then((r) => {
            setResult(r)
            setStatus("ready")
            setError(null)
          })
          .catch((e: Error) => {
            setError(e.message)
            setStatus("error")
          })
      }
    }, 400)
  }, [conversationId])

  const reset = useCallback(() => {
    setResult(null)
    setStatus(wsRef.current?.readyState === WebSocket.OPEN ? "ready" : "idle")
    setError(null)
  }, [])

  return { result, status, error, analyze, reset }
}
