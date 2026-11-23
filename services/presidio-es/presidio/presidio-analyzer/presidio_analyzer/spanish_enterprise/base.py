"""Base class for Spanish enterprise pattern recognizers."""

from __future__ import annotations

from typing import List, Optional, Set

from presidio_analyzer import PatternRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts
from presidio_analyzer.spanish_enterprise.utils import (
    DEFAULT_CONTEXT_WINDOW_CHARS,
    EntityScore,
    align_results_to_original_text,
    has_context_term,
    normalize_enterprise_text,
    trim_span,
)


class SpanishEnterprisePatternRecognizer(PatternRecognizer):
    """Pattern recognizer with normalization, context scoring, and blacklist support."""

    CONTEXT_WINDOW_CHARS = DEFAULT_CONTEXT_WINDOW_CHARS

    def __init__(
        self,
        *args,
        blacklist: Optional[Set[str]] = None,
        context_boost_terms: Optional[Set[str]] = None,
        context_window_chars: int = DEFAULT_CONTEXT_WINDOW_CHARS,
        entity_score: Optional[EntityScore] = None,
        require_context: bool = False,
        **kwargs,
    ):
        self.blacklist = blacklist or set()
        self.context_boost_terms = context_boost_terms or set(self.context or [])
        self.context_window_chars = context_window_chars
        self.entity_score = entity_score or EntityScore(base=0.45, with_context=0.75)
        self.require_context = require_context
        super().__init__(*args, **kwargs)

    def analyze(
        self,
        text: str,
        entities: List[str],
        nlp_artifacts: Optional[NlpArtifacts] = None,
        regex_flags: Optional[int] = None,
    ) -> List[RecognizerResult]:
        if self.supported_entities[0] not in entities:
            return []

        normalized_text = normalize_enterprise_text(text)
        candidate_groups = [(text, False)]
        if normalized_text != text:
            candidate_groups.append((normalized_text, True))

        validated: List[RecognizerResult] = []
        seen_spans: Set[tuple[int, int]] = set()

        for source_text, from_normalized in candidate_groups:
            candidates = super().analyze(
                text=source_text,
                entities=entities,
                nlp_artifacts=nlp_artifacts,
                regex_flags=regex_flags,
            )
            for result in candidates:
                span_text = source_text[result.start : result.end]
                if not self.validate_result(span_text):
                    normalized_span = normalize_enterprise_text(span_text)
                    if normalized_span != span_text and self.validate_result(normalized_span):
                        span_text = normalized_span
                    else:
                        continue

                if from_normalized:
                    aligned = align_results_to_original_text(
                        original_text=text,
                        normalized_text=normalized_text,
                        span_text=span_text,
                        normalized_start=result.start,
                        normalized_end=result.end,
                    )
                else:
                    aligned = trim_span(text, result.start, result.end)

                if aligned is None:
                    continue

                start, end = aligned
                if start >= end or (start, end) in seen_spans:
                    continue
                seen_spans.add((start, end))

                result.start, result.end = start, end
                has_context = has_context_term(
                    text,
                    result.start,
                    result.end,
                    self.context_boost_terms,
                    self.context_window_chars,
                )
                score = self.entity_score.resolve(
                    has_context=has_context,
                    allow_fallback=not self.require_context,
                )
                if score is None:
                    continue

                result.score = score
                validated.append(result)

        return validated
