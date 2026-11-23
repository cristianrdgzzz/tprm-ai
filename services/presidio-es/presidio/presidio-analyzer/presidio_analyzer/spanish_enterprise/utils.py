"""Shared utilities for Spanish enterprise recognizers."""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import FrozenSet, Iterable, Optional, Set

import regex

logger = logging.getLogger("presidio-analyzer")

REGEX_TIMEOUT_SECONDS = int(os.environ.get("REGEX_TIMEOUT_SECONDS", 60))
DEFAULT_CONTEXT_WINDOW_CHARS = 150

_OCR_REPLACEMENTS = (
    ("\u2018", "'"),
    ("\u2019", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u00a0", " "),
    ("\u200b", ""),
    ("\u00ad", ""),
    ("\ufeff", ""),
)


def normalize_enterprise_text(text: str) -> str:
    """Normalize whitespace and common OCR artifacts for validation only."""
    normalized = unicodedata.normalize("NFKC", text)
    for source, target in _OCR_REPLACEMENTS:
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"[\u200b\u00ad\ufeff]", "", normalized)
    normalized = re.sub(r"[ \t\r\n]+", " ", normalized)
    normalized = re.sub(r" +", " ", normalized)
    return normalized.strip()


def normalize_token(token: str) -> str:
    return token.strip(".,;:!?()[]\"'«»").lower()


def trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Trim leading/trailing whitespace from a span while keeping valid bounds."""
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def extract_context_window(text: str, start: int, end: int, window_chars: int) -> str:
    window_start = max(0, start - window_chars)
    window_end = min(len(text), end + window_chars)
    return text[window_start:window_end]


def has_context_term(
    text: str,
    start: int,
    end: int,
    terms: Iterable[str],
    window_chars: int = DEFAULT_CONTEXT_WINDOW_CHARS,
) -> bool:
    snippet = extract_context_window(text, start, end, window_chars)
    for term in terms:
        try:
            if regex.search(
                rf"(?i)\b{regex.escape(term)}\b",
                snippet,
                timeout=REGEX_TIMEOUT_SECONDS,
            ):
                return True
        except TimeoutError:
            logger.warning(
                "Context term search timed out for %r", term, exc_info=True
            )
    return False


def contains_blacklisted_token(text: str, blacklist: Set[str]) -> bool:
    for token in text.split():
        if normalize_token(token) in blacklist:
            return True
    return False


def is_title_case_token(token: str, min_length: int = 3) -> bool:
    cleaned = token.strip(".,;:!?()[]\"'«»")
    if len(cleaned) < min_length:
        return False
    if not cleaned[0].isupper():
        return False
    if cleaned.isupper() and len(cleaned) <= 5:
        return False
    return bool(
        re.fullmatch(r"[A-ZÁÉÍÓÚÑÜ][A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9&.'\-]*", cleaned)
    )


def is_acronym_token(token: str) -> bool:
    cleaned = token.strip(".,;:!?()[]\"'«»")
    return bool(re.fullmatch(r"[A-Z0-9]{2,8}", cleaned))


@dataclass(frozen=True)
class EntityScore:
    base: float
    with_context: float
    without_context: Optional[float] = None

    def resolve(self, has_context: bool, allow_fallback: bool = True) -> Optional[float]:
        if has_context:
            return self.with_context
        if allow_fallback and self.without_context is not None:
            return self.without_context
        if allow_fallback:
            return self.base
        return None


def _flexible_whitespace_pattern(span_text: str) -> str:
    tokens = [token for token in span_text.split() if token]
    if not tokens:
        return ""
    return r"\s+".join(regex.escape(token) for token in tokens)


def align_results_to_original_text(
    original_text: str,
    normalized_text: str,
    span_text: str,
    normalized_start: Optional[int] = None,
    normalized_end: Optional[int] = None,
) -> Optional[tuple[int, int]]:
    """Map a matched span back to exact offsets in the original document text."""
    if not span_text:
        return None

    exact_index = original_text.find(span_text)
    if exact_index >= 0:
        return exact_index, exact_index + len(span_text)

    lowered_original = original_text.lower()
    lowered_span = span_text.lower()
    case_insensitive_index = lowered_original.find(lowered_span)
    if case_insensitive_index >= 0:
        return case_insensitive_index, case_insensitive_index + len(span_text)

    flexible_pattern = _flexible_whitespace_pattern(span_text)
    if flexible_pattern:
        try:
            match = regex.search(
                rf"(?i)\b{flexible_pattern}\b",
                original_text,
                timeout=REGEX_TIMEOUT_SECONDS,
            )
            if match:
                return match.start(), match.end()
        except TimeoutError:
            logger.warning(
                "Flexible alignment regex timed out for span %r", span_text, exc_info=True
            )

    if normalized_start is not None and normalized_end is not None:
        if normalized_end <= len(normalized_text):
            candidate = normalized_text[normalized_start:normalized_end]
            flexible_pattern = _flexible_whitespace_pattern(candidate)
            if flexible_pattern:
                try:
                    match = regex.search(
                        rf"(?i)\b{flexible_pattern}\b",
                        original_text,
                        timeout=REGEX_TIMEOUT_SECONDS,
                    )
                    if match:
                        return match.start(), match.end()
                except TimeoutError:
                    logger.warning(
                        "Flexible alignment regex timed out for candidate %r",
                        candidate,
                        exc_info=True,
                    )

    return None


NAME_PARTICLES: FrozenSet[str] = frozenset({"de", "del", "la", "los", "las"})
CONJUNCTION_TOKENS: FrozenSet[str] = frozenset({"y", "e", "o", "u"})


def contains_conjunction(text: str) -> bool:
    """Return True when the span contains coordinating conjunctions between tokens."""
    for token in text.split():
        if normalize_token(token) in CONJUNCTION_TOKENS:
            return True
    return False


def is_short_uppercase_span(span_text: str, max_length: int = 5) -> bool:
    cleaned = span_text.strip()
    return bool(cleaned) and cleaned.isupper() and len(cleaned) <= max_length
