"use client"

import { SWRConfig } from "swr"
import type { ReactNode } from "react"

export function SWRProvider({ children }: { children: ReactNode }) {
  return (
    <SWRConfig
      value={{
        dedupingInterval: 5_000,      // collapse identical requests within 5s
        focusThrottleInterval: 10_000, // throttle revalidate-on-focus to once per 10s
        errorRetryCount: 3,
        errorRetryInterval: 5_000,
        revalidateOnFocus: false,      // prevent unnecessary re-fetches on tab switch
        shouldRetryOnError: true,
      }}
    >
      {children}
    </SWRConfig>
  )
}
