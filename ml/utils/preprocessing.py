"""
FreeAssist — Text Preprocessing

Orchestrates presidio (PII), spacy (NER), clean-text and ftfy.
We don't reinvent the wheel — we compose proven libraries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

try:
    import ftfy
    _HAS_FTFY = True
except ImportError:
    _HAS_FTFY = False

try:
    from cleantext import clean as _clean_text
    _HAS_CLEANTEXT = True
except ImportError:
    _HAS_CLEANTEXT = False

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    _HAS_PRESIDIO = True
except ImportError:
    _HAS_PRESIDIO = False


# ---------------------------------------------------------------------------
# Lazy singletons — loaded once, reused across calls (full ML mode only)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_analyzer():  # type: ignore[return]
    if not _HAS_PRESIDIO:
        return None
    return AnalyzerEngine()


@lru_cache(maxsize=1)
def _get_anonymizer():  # type: ignore[return]
    if not _HAS_PRESIDIO:
        return None
    return AnonymizerEngine()


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ProcessedText:
    original: str
    cleaned: str
    pii_entities: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

_CLEAN_OPTS = dict(
    fix_unicode=True,
    to_ascii=False,        # keep French accents
    lower=False,
    no_line_breaks=True,
    no_urls=True,
    no_emails=True,
    no_phone_numbers=True,
    no_numbers=False,
    no_punct=False,
    replace_with_url="[URL]",
    replace_with_email="[EMAIL]",
    replace_with_phone_number="[PHONE]",
    lang="fr",
)


def preprocess(text: str, anonymize_pii: bool = True) -> ProcessedText:
    """
    Full preprocessing pipeline. Degrades gracefully when ML libs absent:
      1. ftfy        — fix encoding artifacts (skipped if not installed)
      2. clean-text  — normalize URLs, emails, phones (skipped if not installed)
      3. presidio    — detect and mask PII (skipped if not installed)
    """
    original = text

    if _HAS_FTFY:
        text = ftfy.fix_text(text)

    if _HAS_CLEANTEXT:
        text = _clean_text(text, **_CLEAN_OPTS)

    pii_found: list[str] = []

    if anonymize_pii and _HAS_PRESIDIO:
        analyzer = _get_analyzer()
        anonymizer = _get_anonymizer()
        if analyzer and anonymizer:
            results = analyzer.analyze(text=text, language="fr")
            pii_found = [r.entity_type for r in results]
            if results:
                text = anonymizer.anonymize(text=text, analyzer_results=results).text

    return ProcessedText(original=original, cleaned=text, pii_entities=pii_found)


def preprocess_conversation(turns: list[dict], anonymize_pii: bool = True) -> list[dict]:
    """Apply preprocessing to user turns only; agent turns are already professional."""
    result = []
    for turn in turns:
        if turn["role"] == "user":
            processed = preprocess(turn["content"], anonymize_pii=anonymize_pii)
            result.append({**turn, "content": processed.cleaned})
        else:
            result.append(turn)
    return result


def build_classification_input(turns: list[dict], strategy: str = "first_turn") -> str:
    """
    Collapse a conversation into a single string for the intent classifier.

    Strategies:
      first_turn   — first user message only (low latency, good baseline)
      concat_user  — all user messages joined (more context)
      full         — all turns serialized (max context, slower)
    """
    user_turns = [t["content"] for t in turns if t["role"] == "user"]
    if not user_turns:
        return ""
    match strategy:
        case "first_turn":
            return user_turns[0]
        case "concat_user":
            return " [SEP] ".join(user_turns)
        case "full":
            return " ".join(f"[{t['role'].upper()}] {t['content']}" for t in turns)
        case _:
            raise ValueError(f"Unknown strategy: {strategy!r}")
