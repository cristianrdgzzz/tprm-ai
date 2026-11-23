"""Spanish organization recognizer for multi-token certifier/vendor names."""

from __future__ import annotations

from typing import FrozenSet, List, Optional, Set

from presidio_analyzer import Pattern
from presidio_analyzer.spanish_enterprise.base import SpanishEnterprisePatternRecognizer
from presidio_analyzer.spanish_enterprise.utils import (
    EntityScore,
    contains_blacklisted_token,
    is_short_uppercase_span,
    normalize_token,
)

ORGANIZATION_DENYLIST: FrozenSet[str] = frozenset(
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
        "gdpr",
        "nif",
        "cif",
        "iban",
        "saas",
    }
)

ORGANIZATION_CONTEXT_TERMS: tuple[str, ...] = (
    "certificador",
    "certificación",
    "certificacion",
    "auditor",
    "proveedor",
    "empresa",
    "organización",
    "organizacion",
    "vendor",
    "socio",
    "certificado por",
    "certificado",
    "norma",
    "estándar",
    "estandar",
    "acreditado",
    "registrado",
    "emitido por",
)

CONTEXT_PREFIXES: tuple[str, ...] = (
    "certificado por ",
    "certificado ",
    "emitido por ",
    "auditado por ",
    "proveedor ",
    "empresa ",
)

REJECT_FIRST_TOKENS: FrozenSet[str] = frozenset(
    {
        "accesos",
        "transferencias",
        "subcontratistas",
        "análisis",
        "gestión",
        "conclusion",
        "conclusión",
        "controles",
        "riesgo",
        "base",
        "alcance",
        "actividad",
        "infraestructura",
        "certificado",
    }
)

_ORG_TOKEN = r"[A-ZÁÉÍÓÚÑÜ][A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9&.'\-]*"
_ORG_NAME = rf"\b{_ORG_TOKEN}(?:\s+{_ORG_TOKEN}){{1,4}}\b"


class EsSpanishOrganizationRecognizer(SpanishEnterprisePatternRecognizer):
    """Detect multi-token organization names such as ``SGS ICS Iberia``."""

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern("Spanish multi-token organization", _ORG_NAME, 0.55),
    ]

    CONTEXT = list(ORGANIZATION_CONTEXT_TERMS)

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
            blacklist=set(blacklist) if blacklist is not None else set(ORGANIZATION_DENYLIST),
            context_boost_terms=set(ORGANIZATION_CONTEXT_TERMS),
            entity_score=EntityScore(base=0.0, with_context=0.75, without_context=0.0),
            require_context=True,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        stripped = pattern_text.strip()

        lowered_stripped = stripped.lower()
        for prefix in CONTEXT_PREFIXES:
            if lowered_stripped.startswith(prefix):
                stripped = stripped[len(prefix) :]
                break

        if "\n" in stripped or "\r" in stripped:
            return False

        if len(stripped) > 60:
            return False

        if is_short_uppercase_span(stripped):
            return False

        if contains_blacklisted_token(stripped, self.blacklist):
            return False

        tokens = [token for token in stripped.split() if token]

        if len(tokens) < 2 or len(tokens) > 5:
            return False

        if not all(token[0].isupper() for token in tokens):
            return False

        if normalize_token(tokens[0]) in REJECT_FIRST_TOKENS:
            return False

        if all(normalize_token(token) in self.blacklist for token in tokens):
            return False

        lowered = stripped.lower()
        if any(
            suffix in lowered
            for suffix in (" s.l.", " s.a.", " s.l.u.", " s.a.u.", " sl", " sa")
        ):
            return False

        return True
