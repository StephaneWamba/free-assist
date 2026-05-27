"""FreeAssist — Knowledge base browse + upload route."""

from __future__ import annotations

import re
import time
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])

KB_ROOT = Path(__file__).parents[5] / "data" / "knowledge_base"
if not KB_ROOT.exists():
    KB_ROOT = Path("/app/data/knowledge_base")

CATEGORY_LABELS = {
    "procedures": "Procédures",
    "faq": "FAQ",
    "billing": "Facturation",
    "technical": "Technique",
    "offers": "Offres",
}

ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "-", name.lower()).strip("-")


def _parse_doc(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else path.stem
    preview = " ".join(
        line.strip() for line in lines[1:] if line.strip() and not line.startswith("#")
    )[:200]
    return {
        "id": _slug(path.stem),
        "title": title,
        "category": path.parent.name,
        "category_label": CATEGORY_LABELS.get(path.parent.name, path.parent.name),
        "filename": path.name,
        "preview": preview,
        "content": raw,
        "word_count": len(raw.split()),
    }


_docs_cache: list[dict] = []
_docs_cache_at: float = 0.0
_CACHE_TTL = 60.0


def _invalidate_cache() -> None:
    global _docs_cache, _docs_cache_at
    _docs_cache = []
    _docs_cache_at = 0.0


def _all_docs() -> list[dict]:
    global _docs_cache, _docs_cache_at
    now = time.monotonic()
    if _docs_cache and now - _docs_cache_at < _CACHE_TTL:
        return _docs_cache
    if not KB_ROOT.exists():
        return []
    docs = []
    for md in sorted(KB_ROOT.rglob("*.md")):
        try:
            docs.append(_parse_doc(md))
        except Exception:
            pass
    _docs_cache = docs
    _docs_cache_at = now
    return docs


def _extract_text_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        parts = []
        for page in reader.pages:
            text = page.extract_text() or ""
            parts.append(text)
        return "\n\n".join(parts)
    except Exception as exc:
        raise HTTPException(422, f"Impossible de lire le PDF : {exc}") from exc


def _extract_text_docx(data: bytes) -> str:
    try:
        import docx
        doc = docx.Document(BytesIO(data))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as exc:
        raise HTTPException(422, f"Impossible de lire le DOCX : {exc}") from exc


def _to_markdown(filename: str, text: str) -> str:
    stem = Path(filename).stem
    title = stem.replace("_", " ").replace("-", " ").title()
    return f"# {title}\n\n{text}"


@router.get("")
async def list_docs(
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
) -> JSONResponse:
    all_docs = _all_docs()
    docs = all_docs

    if category:
        docs = [d for d in docs if d["category"] == category]

    if q:
        ql = q.lower()
        docs = [
            d for d in docs
            if ql in d["title"].lower() or ql in d["preview"].lower() or ql in d["content"].lower()
        ]

    all_categories = sorted({d["category"] for d in all_docs})
    categories = [
        {"id": c, "label": CATEGORY_LABELS.get(c, c.capitalize())}
        for c in all_categories
    ]
    payload = {
        "total": len(docs),
        "categories": categories,
        "docs": [{k: v for k, v in d.items() if k != "content"} for d in docs],
    }
    cache = "public, max-age=30" if not q else "no-store"
    return JSONResponse(content=payload, headers={"Cache-Control": cache})


@router.get("/{doc_id}")
async def get_doc(doc_id: str) -> JSONResponse:
    docs = _all_docs()
    doc = next((d for d in docs if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return JSONResponse(content=doc, headers={"Cache-Control": "public, max-age=60"})


@router.post("/upload")
async def upload_doc(
    file: UploadFile = File(...),
    category: str = Form(...),
) -> JSONResponse:
    if not file.filename:
        raise HTTPException(400, "Nom de fichier manquant")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            415,
            f"Format non supporté : {ext}. Formats acceptés : {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Sanitize category name
    category = re.sub(r"[^a-z0-9_-]", "-", category.lower()).strip("-") or "general"

    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, f"Fichier trop lourd (max {MAX_FILE_BYTES // 1024 // 1024} MB)")

    # Convert to markdown text
    if ext in (".md", ".txt"):
        text = data.decode("utf-8", errors="replace")
        if ext == ".txt":
            text = _to_markdown(file.filename, text)
    elif ext == ".pdf":
        text = _to_markdown(file.filename, _extract_text_pdf(data))
    elif ext == ".docx":
        text = _to_markdown(file.filename, _extract_text_docx(data))
    else:
        raise HTTPException(415, "Format non supporté")

    # Save to KB directory
    dest_dir = KB_ROOT / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = _slug(Path(file.filename).stem)
    dest_path = dest_dir / f"{stem}.md"

    dest_path.write_text(text, encoding="utf-8")
    _invalidate_cache()

    doc = _parse_doc(dest_path)
    return JSONResponse(
        content={"success": True, "doc": {k: v for k, v in doc.items() if k != "content"}},
        status_code=201,
    )


@router.delete("/{doc_id}")
async def delete_doc(doc_id: str) -> JSONResponse:
    docs = _all_docs()
    doc = next((d for d in docs if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(404, "Document not found")

    path = KB_ROOT / doc["category"] / doc["filename"]
    if path.exists():
        path.unlink()
    _invalidate_cache()
    return JSONResponse(content={"success": True})
