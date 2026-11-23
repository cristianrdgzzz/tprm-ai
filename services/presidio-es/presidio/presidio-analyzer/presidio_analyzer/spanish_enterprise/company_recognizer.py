"""Spanish COMPANY recognizer for legal-entity suffixes in enterprise documents."""

from __future__ import annotations

import re
from typing import FrozenSet, List, Optional, Set

from presidio_analyzer import Pattern
from presidio_analyzer.spanish_enterprise.base import SpanishEnterprisePatternRecognizer
from presidio_analyzer.spanish_enterprise.utils import (
    EntityScore,
    contains_blacklisted_token,
    is_acronym_token,
    is_short_uppercase_span,
    is_title_case_token,
    normalize_token,
)

COMPANY_ALLOWED_SHORT_UPPERCASE: FrozenSet[str] = frozenset()

COMPANY_BLACKLIST: FrozenSet[str] = frozenset(
    {
        "iso",
        "mfa",
        "rpo",
        "rto",
        "bcp",
        "saas",
        "gdpr",
        "rgpd",
        "lopd",
        "soc",
        "siem",
        "iam",
        "vpn",
        "api",
        "erp",
        "crm",
        "it",
        "ti",
        "dpo",
        "cto",
        "cfo",
        "ceo",
        "ciso",
        "kpi",
        "sla",
        "scc",
        "tia",
        "rpa",
        "edr",
        "xdr",
        "ueba",
        "pii",
        "phi",
        "nif",
        "cif",
        "iban",
    }
)

COMPANY_CONTEXT_TERMS: tuple[str, ...] = (
    "empresa",
    "proveedor",
    "compañía",
    "compania",
    "cliente",
    "sociedad",
    "razón social",
    "razon social",
)

_LEGAL_SUFFIX = (
    r"(?:S\.?\s*L\.?\s*U\.?|S\.?\s*A\.?\s*U\.?|S\.?\s*L\.?|S\.?\s*A\.?|\s+SL|\s+SA)"
)
_COMPANY_NAME_TOKEN = r"[A-ZÁÉÍÓÚÑÜ][A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9&.'\-]*"
_COMPANY_NAME = (
    rf"(?:{_COMPANY_NAME_TOKEN}(?:\s+{_COMPANY_NAME_TOKEN}){{0,7}}\s+)"
)


_LEADING_STOPWORD_GUARD = (
    r"(?!(?-i:El|La|Los|Las|Un|Una|Al|Del|De|Por|Para|Con|En|Y|Empresa|Proveedor|Certificado)\s)"
)


class EsSpanishCompanyRecognizer(SpanishEnterprisePatternRecognizer):
    """Detect Spanish companies with legal suffixes and enterprise context validation."""

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern(
            "Spanish company with legal suffix",
            # Name tokens must start with an uppercase letter even though Presidio compiles
            # patterns with IGNORECASE: (?-i:...) keeps the name case-sensitive so spans do
            # not swallow preceding lowercase words ("emitido a", "El proveedor"...).
            rf"\b{_LEADING_STOPWORD_GUARD}(?-i:{_COMPANY_NAME}){_LEGAL_SUFFIX}\b",
            0.45,
        ),
    ]

    CONTEXT = list(COMPANY_CONTEXT_TERMS)
    MIN_TITLE_CASE_TOKENS = 2

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "COMPANY",
        blacklist: Optional[Set[str]] = None,
        name: Optional[str] = None,
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns or self.PATTERNS,
            context=context or self.CONTEXT,
            supported_language=supported_language,
            blacklist=set(blacklist) if blacklist is not None else set(COMPANY_BLACKLIST),
            context_boost_terms=set(COMPANY_CONTEXT_TERMS),
            entity_score=EntityScore(base=0.45, with_context=0.78, without_context=0.45),
            require_context=False,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        stripped = pattern_text.strip()
        normalized_span = normalize_token(stripped)

        if normalized_span in COMPANY_ALLOWED_SHORT_UPPERCASE:
            return True

        if is_short_uppercase_span(stripped):
            return False

        if contains_blacklisted_token(pattern_text, self.blacklist):
            return False

        if re.match(r"^[A-Z]{2}[-/][A-Z0-9]", stripped):
            return False

        if not self._has_valid_legal_suffix(pattern_text):
            return False

        return self._validate_legal_suffix_company(pattern_text)

    def _validate_legal_suffix_company(self, pattern_text: str) -> bool:
        name_part, suffix = self._split_name_and_suffix(pattern_text)
        if not name_part or not suffix:
            return False

        name_tokens = [token for token in name_part.split() if token]
        if not name_tokens:
            return False

        if len(name_tokens) == 1:
            if is_acronym_token(name_tokens[0]):
                return False
            if not is_title_case_token(name_tokens[0], min_length=2):
                return False
        else:
            if all(is_acronym_token(token) for token in name_tokens):
                return False
            title_case_tokens = [
                token for token in name_tokens if is_title_case_token(token, min_length=2)
            ]
            if len(title_case_tokens) < self.MIN_TITLE_CASE_TOKENS:
                return False

        if normalize_token(suffix) in {"sa", "sl"}:
            last_token = normalize_token(name_tokens[-1])
            if last_token in self.blacklist or last_token in {"saas", "mesa", "data", "meta"}:
                return False

        return True

    @staticmethod
    def _split_name_and_suffix(pattern_text: str) -> tuple[str, str]:
        suffix_patterns = (
            r"\s+S\.?\s*L\.?\s*U\.?\s*$",
            r"\s+S\.?\s*A\.?\s*U\.?\s*$",
            r"\s+S\.?\s*L\.?\s*$",
            r"\s+S\.?\s*A\.?\s*$",
            r"\s+SL\s*$",
            r"\s+SA\s*$",
        )
        for suffix_pattern in suffix_patterns:
            match = re.search(suffix_pattern, pattern_text, flags=re.IGNORECASE)
            if match:
                return pattern_text[: match.start()].strip(), pattern_text[match.start() :].strip()
        return "", ""

    @staticmethod
    def _has_valid_legal_suffix(pattern_text: str) -> bool:
        return bool(
            re.search(
                r"(?i)(?:S\.?\s*L\.?\s*U\.?|S\.?\s*A\.?\s*U\.?|S\.?\s*L\.?|S\.?\s*A\.?|\sSL|\sSA)\s*$",
                pattern_text,
            )
        )
