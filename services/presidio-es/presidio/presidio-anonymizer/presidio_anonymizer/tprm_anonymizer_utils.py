"""Utilities for TPRM anonymization: denylist filtering and span conflict resolution."""

from __future__ import annotations

import re
from typing import FrozenSet, List, Set

from presidio_anonymizer.entities import RecognizerResult

TPRM_TECHNICAL_DENYLIST: FrozenSet[str] = frozenset(
    {
        "iso",
        "mfa",
        "bcp",
        "rpo",
        "rto",
        "sla",
        "scc",
        "tia",
        "dpo",
        "aws",
        "gdpr",
        "nif",
        "cif",
        "iban",
        "saas",
        "rgpd",
        "soc",
        "siem",
        "kpi",
        "api",
        "erp",
        "crm",
        "pii",
        "phi",
    }
)

COMPANY_ORG_ENTITY_TYPES: FrozenSet[str] = frozenset(
    {"COMPANY", "ORGANIZATION", "ORG"}
)

MAX_ENTITY_SPAN_CHARS = 80
MAX_ENTITY_SPAN_TOKENS = 6


def normalize_denylist_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def is_denylisted_span(span_text: str, denylist: Set[str] | None = None) -> bool:
    """Return True when the full span is a technical acronym that must not be tagged."""
    denylist = denylist or set(TPRM_TECHNICAL_DENYLIST)
    cleaned = span_text.strip()
    if not cleaned:
        return True

    normalized = normalize_denylist_token(cleaned)
    if normalized in denylist:
        return True

    tokens = [token for token in re.split(r"\s+", cleaned) if token]
    if len(tokens) == 1 and normalize_denylist_token(tokens[0]) in denylist:
        return True

    return False


def trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Trim leading/trailing whitespace from a span while keeping valid bounds."""
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def get_span_text(text: str, start: int, end: int) -> str:
    """Return the exact matched entity text from the source document."""
    trimmed_start, trimmed_end = trim_span(text, start, end)
    return text[trimmed_start:trimmed_end]


def is_corrupt_span(text: str, start: int, end: int) -> bool:
    """Return True when a span crosses lines or captures non-entity text."""
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    if start >= end:
        return True

    raw_span = text[start:end]
    if "\n" in raw_span or "\r" in raw_span:
        return True

    stripped = raw_span.strip()
    if not stripped:
        return True

    if len(stripped) > MAX_ENTITY_SPAN_CHARS:
        return True

    if len(stripped.split()) > MAX_ENTITY_SPAN_TOKENS:
        return True

    return False


def filter_corrupt_spans(
    analyzer_results: List[RecognizerResult],
    text: str,
) -> List[RecognizerResult]:
    """Remove spans that cross paragraph breaks or cover non-entity text."""
    filtered: List[RecognizerResult] = []

    for result in analyzer_results:
        if is_corrupt_span(text, result.start, result.end):
            continue

        filtered.append(
            RecognizerResult(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=result.score,
            )
        )

    return filtered


def deduplicate_overlapping(
    analyzer_results: List[RecognizerResult],
    text: str,
) -> List[RecognizerResult]:
    """Keep the highest-scoring entity for each overlapping span."""
    candidates = sorted(
        analyzer_results,
        key=lambda result: (-result.score, -(result.end - result.start), result.start),
    )
    kept: List[RecognizerResult] = []
    for candidate in candidates:
        candidate_start, candidate_end = trim_span(text, candidate.start, candidate.end)
        if candidate_start >= candidate_end:
            continue

        overlaps_existing = False
        for existing in kept:
            existing_start, existing_end = trim_span(text, existing.start, existing.end)
            overlap_start = max(candidate_start, existing_start)
            overlap_end = min(candidate_end, existing_end)
            if overlap_start < overlap_end:
                overlaps_existing = True
                break

        if overlaps_existing:
            continue

        kept.append(
            RecognizerResult(
                entity_type=candidate.entity_type,
                start=candidate_start,
                end=candidate_end,
                score=candidate.score,
            )
        )

    return sorted(kept, key=lambda result: (result.start, result.end))


def filter_denylisted_entities(
    analyzer_results: List[RecognizerResult],
    text: str,
    denylist: Set[str] | None = None,
) -> List[RecognizerResult]:
    """Remove technical acronyms and empty spans."""
    denylist = denylist or set(TPRM_TECHNICAL_DENYLIST)
    filtered: List[RecognizerResult] = []

    for result in analyzer_results:
        trimmed_start, trimmed_end = trim_span(text, result.start, result.end)
        if trimmed_start >= trimmed_end:
            continue

        span_text = text[trimmed_start:trimmed_end]
        if result.entity_type in COMPANY_ORG_ENTITY_TYPES and is_denylisted_span(
            span_text, denylist
        ):
            continue

        filtered.append(
            RecognizerResult(
                entity_type=result.entity_type,
                start=trimmed_start,
                end=trimmed_end,
                score=result.score,
            )
        )

    return filtered


def prepare_analyzer_results(
    text: str,
    analyzer_results: List[RecognizerResult],
    denylist: Set[str] | None = None,
) -> List[RecognizerResult]:
    """Sanitize spans, apply denylist, and resolve overlapping detections."""
    sanitized = filter_corrupt_spans(analyzer_results, text)
    sanitized = filter_denylisted_entities(sanitized, text, denylist=denylist)
    return deduplicate_overlapping(sanitized, text)
