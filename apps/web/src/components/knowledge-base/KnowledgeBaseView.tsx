"use client"

import { useRef, useState } from "react"
import ReactMarkdown from "react-markdown"
import {
  Search,
  FileText,
  ChevronRight,
  X,
  Loader2,
  BookOpen,
  Upload,
  Trash2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react"
import { useKnowledgeDocs, useKnowledgeDoc } from "@/hooks/useKnowledgeBase"
import { api } from "@/lib/api"
import type { KBDoc } from "@/lib/api"

const ACCEPTED = ".md,.txt,.pdf,.docx"
const CATEGORIES = [
  { id: "procedures", label: "Procédures" },
  { id: "faq", label: "FAQ" },
  { id: "billing", label: "Facturation" },
  { id: "technical", label: "Technique" },
  { id: "offers", label: "Offres" },
]

// ─── DocContent ───────────────────────────────────────────────────────────────

function DocContent({
  id,
  onClose,
  onDelete,
}: {
  id: string
  onClose: () => void
  onDelete: (id: string) => void
}) {
  const { data, isLoading } = useKnowledgeDoc(id)
  const [deleting, setDeleting] = useState(false)

  async function handleDelete() {
    if (!confirm("Supprimer ce document ?")) return
    setDeleting(true)
    try {
      await api.knowledgeBase.delete(id)
      onDelete(id)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-[#1e1e1e] p-4">
        <div>
          {isLoading ? (
            <div className="h-4 w-48 bg-[#1e1e1e] rounded animate-pulse" />
          ) : (
            <p className="text-sm font-semibold text-white">{data?.title}</p>
          )}
          {data && (
            <p className="text-[11px] text-zinc-500 mt-0.5">
              {data.category_label} · {data.word_count} mots
            </p>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="rounded-lg p-1.5 text-zinc-600 hover:bg-red-900/20 hover:text-red-400 transition-colors"
            title="Supprimer"
          >
            {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-500 hover:bg-[#1e1e1e] hover:text-zinc-300 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-5">
        {isLoading ? (
          <div className="flex items-center justify-center h-32 gap-2 text-zinc-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">Chargement…</span>
          </div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none text-zinc-300 [&_h1]:text-white [&_h1]:text-base [&_h1]:font-semibold [&_h1]:mb-3 [&_h2]:text-zinc-200 [&_h2]:text-[13px] [&_h2]:font-semibold [&_h2]:mt-5 [&_h2]:mb-2 [&_h3]:text-zinc-300 [&_h3]:text-[12px] [&_h3]:font-medium [&_h3]:mt-4 [&_h3]:mb-1.5 [&_p]:text-[13px] [&_p]:leading-relaxed [&_p]:text-zinc-400 [&_strong]:text-zinc-200 [&_strong]:font-semibold [&_ul]:text-[13px] [&_ul]:text-zinc-400 [&_ol]:text-[13px] [&_ol]:text-zinc-400 [&_li]:leading-relaxed [&_table]:text-[12px] [&_table]:w-full [&_th]:text-left [&_th]:text-zinc-400 [&_th]:font-medium [&_th]:pb-1 [&_td]:text-zinc-400 [&_td]:py-0.5 [&_tr]:border-b [&_tr]:border-[#2a2a2a] [&_code]:text-[#E2001A] [&_code]:bg-[#1a1a1a] [&_code]:px-1 [&_code]:rounded">
            <ReactMarkdown>{data?.content ?? ""}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── DocRow ───────────────────────────────────────────────────────────────────

function DocRow({ doc, selected, onSelect }: { doc: KBDoc; selected: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`w-full flex items-start gap-3 rounded-lg p-3.5 text-left transition-colors ${
        selected ? "bg-[#E2001A]/10 border border-[#E2001A]/20" : "hover:bg-[#1a1a1a] border border-transparent"
      }`}
    >
      <FileText className={`h-4 w-4 mt-0.5 shrink-0 ${selected ? "text-[#E2001A]" : "text-zinc-500"}`} />
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-medium text-zinc-200 truncate">{doc.title}</p>
        <p className="text-[11px] text-zinc-500 mt-0.5 line-clamp-2">{doc.preview}</p>
        <div className="flex items-center gap-2 mt-1.5">
          <span className="text-[10px] text-zinc-600 bg-[#1e1e1e] px-1.5 py-0.5 rounded">
            {doc.category_label}
          </span>
          <span className="text-[10px] text-zinc-600">{doc.word_count} mots</span>
        </div>
      </div>
      <ChevronRight className={`h-3.5 w-3.5 shrink-0 mt-1 ${selected ? "text-[#E2001A]" : "text-zinc-600"}`} />
    </button>
  )
}

// ─── UploadPanel ──────────────────────────────────────────────────────────────

function UploadPanel({ onUploaded }: { onUploaded: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [category, setCategory] = useState("procedures")
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const [dragging, setDragging] = useState(false)

  function pickFile(f: File) {
    setFile(f)
    setResult(null)
  }

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setResult(null)
    try {
      const { doc } = await api.knowledgeBase.upload(file, category)
      setResult({ ok: true, msg: `"${doc.title}" ajouté dans ${doc.category_label}` })
      setFile(null)
      onUploaded()
    } catch (err) {
      setResult({ ok: false, msg: (err as Error).message })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="border-t border-[#1e1e1e] px-3 py-3 space-y-2">
      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault()
          setDragging(false)
          const f = e.dataTransfer.files[0]
          if (f) pickFile(f)
        }}
        onClick={() => fileRef.current?.click()}
        className={`flex flex-col items-center justify-center gap-1 rounded-lg border border-dashed cursor-pointer py-4 transition-colors ${
          dragging ? "border-[#E2001A]/60 bg-[#E2001A]/5" : "border-[#2a2a2a] hover:border-zinc-600"
        }`}
      >
        <Upload className="h-4 w-4 text-zinc-500" />
        {file ? (
          <p className="text-[11px] text-zinc-300 truncate max-w-[180px]">{file.name}</p>
        ) : (
          <p className="text-[11px] text-zinc-600">
            PDF · DOCX · TXT · MD
          </p>
        )}
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={e => { const f = e.target.files?.[0]; if (f) pickFile(f) }}
        />
      </div>

      {/* Category selector */}
      <select
        value={category}
        onChange={e => setCategory(e.target.value)}
        className="w-full rounded-lg bg-[#1a1a1a] border border-[#2a2a2a] px-2.5 py-1.5 text-[12px] text-zinc-300 focus:outline-none focus:border-zinc-600"
      >
        {CATEGORIES.map(c => (
          <option key={c.id} value={c.id}>{c.label}</option>
        ))}
      </select>

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="w-full rounded-lg bg-[#E2001A] px-3 py-1.5 text-[12px] font-medium text-white transition-opacity disabled:opacity-40 hover:opacity-90"
      >
        {uploading ? (
          <span className="flex items-center justify-center gap-1.5">
            <Loader2 className="h-3 w-3 animate-spin" /> Envoi…
          </span>
        ) : "Ajouter à la base"}
      </button>

      {result && (
        <div className={`flex items-start gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] ${
          result.ok ? "bg-emerald-900/20 text-emerald-400" : "bg-red-900/20 text-red-400"
        }`}>
          {result.ok
            ? <CheckCircle2 className="h-3 w-3 mt-0.5 shrink-0" />
            : <AlertCircle className="h-3 w-3 mt-0.5 shrink-0" />}
          {result.msg}
        </div>
      )}
    </div>
  )
}

// ─── KnowledgeBaseView ────────────────────────────────────────────────────────

export function KnowledgeBaseView() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [q, setQ] = useState("")
  const [category, setCategory] = useState<string | undefined>(undefined)
  const [uploadKey, setUploadKey] = useState(0)

  const { data, isLoading, mutate } = useKnowledgeDocs(category, q || undefined)

  function handleUploaded() {
    mutate()
    setUploadKey(k => k + 1)
  }

  function handleDeleted(id: string) {
    setSelectedId(null)
    mutate()
  }

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:h-[calc(100vh-140px)]">
      {/* Left: list + upload */}
      <div className="flex flex-col w-full lg:w-80 lg:shrink-0 rounded-xl border border-[#1e1e1e] bg-[#141414] overflow-hidden max-h-[60vh] lg:max-h-none">
        {/* Search */}
        <div className="p-3 border-b border-[#1e1e1e] space-y-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-600" />
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="Rechercher…"
              className="w-full rounded-lg bg-[#1a1a1a] border border-[#2a2a2a] pl-8 pr-3 py-1.5 text-[13px] text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600"
            />
          </div>
          {data?.categories && (
            <div className="flex gap-1.5 flex-wrap">
              <button
                onClick={() => setCategory(undefined)}
                className={`rounded-full px-2.5 py-0.5 text-[11px] transition-colors ${
                  !category ? "bg-[#E2001A] text-white" : "bg-[#1e1e1e] text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Tout
              </button>
              {data.categories.map(c => (
                <button
                  key={c.id}
                  onClick={() => setCategory(c.id === category ? undefined : c.id)}
                  className={`rounded-full px-2.5 py-0.5 text-[11px] transition-colors ${
                    category === c.id ? "bg-[#E2001A] text-white" : "bg-[#1e1e1e] text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Doc list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isLoading && (
            <div className="flex items-center justify-center h-32 gap-2 text-zinc-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-xs">Chargement…</span>
            </div>
          )}
          {!isLoading && data?.docs.length === 0 && (
            <div className="flex flex-col items-center justify-center h-32 text-zinc-600 gap-2">
              <BookOpen className="h-5 w-5" />
              <span className="text-xs">Aucun document</span>
            </div>
          )}
          {data?.docs.map(doc => (
            <DocRow
              key={doc.id}
              doc={doc}
              selected={doc.id === selectedId}
              onSelect={() => setSelectedId(doc.id === selectedId ? null : doc.id)}
            />
          ))}
        </div>

        <div className="px-3 py-2 border-t border-[#1e1e1e] text-[11px] text-zinc-600">
          {data ? `${data.total} document${data.total > 1 ? "s" : ""}` : "—"}
        </div>

        {/* Upload panel */}
        <UploadPanel key={uploadKey} onUploaded={handleUploaded} />
      </div>

      {/* Right: content */}
      <div className="flex-1 min-h-[300px] rounded-xl border border-[#1e1e1e] bg-[#141414] overflow-hidden">
        {selectedId ? (
          <DocContent
            id={selectedId}
            onClose={() => setSelectedId(null)}
            onDelete={handleDeleted}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-zinc-600">
            <FileText className="h-8 w-8" />
            <p className="text-sm">Sélectionnez un document</p>
            <p className="text-[11px] text-zinc-700">ou importez un fichier PDF, DOCX, TXT, MD</p>
          </div>
        )}
      </div>
    </div>
  )
}
