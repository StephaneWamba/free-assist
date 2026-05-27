import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { SWRProvider } from "@/components/layout/SWRProvider"
import { ThemeProvider } from "@/components/layout/ThemeProvider"
import "./globals.css"

const inter = Inter({ subsets: ["latin"], display: "swap" })

export const metadata: Metadata = {
  title: "FreeAssist - dataX",
  description: "Outil interne pour les agents du support technique Free",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="dark">
      <body className={`${inter.className} bg-white dark:bg-[#0a0a0a] text-zinc-900 dark:text-zinc-100`}>
        <SWRProvider>
          <ThemeProvider>{children}</ThemeProvider>
        </SWRProvider>
      </body>
    </html>
  )
}
