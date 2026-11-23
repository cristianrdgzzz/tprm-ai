"""Strict Spanish PERSON recognizer for enterprise documents."""

from __future__ import annotations

from typing import FrozenSet, List, Optional, Set

from presidio_analyzer import Pattern
from presidio_analyzer.spanish_enterprise.base import SpanishEnterprisePatternRecognizer
from presidio_analyzer.spanish_enterprise.utils import (
    DEFAULT_CONTEXT_WINDOW_CHARS,
    NAME_PARTICLES,
    EntityScore,
    contains_blacklisted_token,
    contains_conjunction,
    is_title_case_token,
    normalize_token,
)

SPANISH_PERSON_BLACKLIST: FrozenSet[str] = frozenset(
    {
        "empresa",
        "actividad",
        "infraestructura",
        "controles",
        "conclusión",
        "conclusion",
        "servicio",
        "proveedor",
        "gestión",
        "gestion",
        "análisis",
        "analisis",
        "saas",
        "software",
        "sistema",
        "documento",
        "informe",
        "sección",
        "seccion",
        "contrato",
        "acuerdo",
        "política",
        "politica",
        "proceso",
        "procedimiento",
        "requisito",
        "medida",
        "riesgo",
        "datos",
        "personal",
        "cliente",
        "usuario",
        "administrador",
        "departamento",
        "equipo",
        "proyecto",
        "solución",
        "solucion",
        "plataforma",
        "tecnología",
        "tecnologia",
        "seguridad",
        "cumplimiento",
        "auditoría",
        "auditoria",
        "evaluación",
        "evaluacion",
        "implementación",
        "implementacion",
        "desarrollo",
        "operación",
        "operacion",
        "mantenimiento",
        "soporte",
        "recursos",
        "capacidad",
        "objetivo",
        "resultado",
        "conclusiones",
        "introducción",
        "introduccion",
        "resumen",
        "anexo",
        "figura",
        "tabla",
        "iso",
        "mfa",
        "rto",
        "bcp",
        "india",
        "méxico",
        "mexico",
        "portugal",
        "francia",
        "alemania",
        "irlanda",
        "españa",
        "espana",
        "europa",
    }
)

PERSON_CONTEXT_TERMS: tuple[str, ...] = (
    "dpo",
    "responsable",
    "contacto",
    "director",
    "manager",
    "nombre",
    "apellidos",
    "firmado",
    "empleado",
    "delegado",
    "protección de datos",
    "proteccion de datos",
)

COMPANY_SUFFIXES: tuple[str, ...] = (
    " s.l.",
    " s.a.",
    " s.l.u.",
    " s.a.u.",
    " sl",
    " sa",
)

_NAME_TOKEN = r"[A-ZÁÉÍÓÚÑÜ][A-Za-zÁÉÍÓÚÑÜáéíóúñü]{2,}"
_NAME_PARTICLE = r"(?:\s+(?:de|del|la|los|las)\s+)"
_TWO_PART_NAME = rf"\b{_NAME_TOKEN}(?:{_NAME_PARTICLE})?{_NAME_TOKEN}\b"
_THREE_PART_NAME = (
    rf"\b{_NAME_TOKEN}(?:{_NAME_PARTICLE})?"
    rf"(?:{_NAME_TOKEN}(?:{_NAME_PARTICLE})?)"
    rf"{_NAME_TOKEN}\b"
)


class EsSpanishPersonRecognizer(SpanishEnterprisePatternRecognizer):
    """
    Strict Spanish PERSON recognizer for enterprise documents.

    Emits fallback score 0.4 without context and 0.8 when role/contact
    terms appear nearby.
    """

    COUNTRY_CODE = "es"
    MIN_TOKEN_LENGTH = 3
    MAX_NAME_TOKENS = 3
    MIN_NAME_TOKENS = 2

    PATTERNS = [
        Pattern("Spanish person (two-part name)", _TWO_PART_NAME, 0.35),
        Pattern("Spanish person (three-part name)", _THREE_PART_NAME, 0.35),
    ]

    CONTEXT = list(PERSON_CONTEXT_TERMS)

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "PERSON",
        blacklist: Optional[Set[str]] = None,
        name: Optional[str] = None,
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns or self.PATTERNS,
            context=context or self.CONTEXT,
            supported_language=supported_language,
            blacklist=set(blacklist) if blacklist is not None else set(SPANISH_PERSON_BLACKLIST),
            context_boost_terms=set(PERSON_CONTEXT_TERMS),
            context_window_chars=DEFAULT_CONTEXT_WINDOW_CHARS,
            entity_score=EntityScore(
                base=0.35,
                with_context=0.8,
                without_context=0.4,
            ),
            require_context=False,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        if contains_conjunction(pattern_text):
            return False

        lowered = pattern_text.lower()
        if any(lowered.endswith(suffix) for suffix in COMPANY_SUFFIXES):
            return False
        if contains_blacklisted_token(pattern_text, self.blacklist):
            return False

        name_tokens = self._extract_name_tokens(pattern_text)
        if len(name_tokens) < self.MIN_NAME_TOKENS or len(name_tokens) > self.MAX_NAME_TOKENS:
            return False

        for token in name_tokens:
            normalized = normalize_token(token)
            if len(normalized) < self.MIN_TOKEN_LENGTH:
                return False
            if normalized in self.blacklist:
                return False
            if not is_title_case_token(token, min_length=self.MIN_TOKEN_LENGTH):
                return False

        return True

    @staticmethod
    def _extract_name_tokens(pattern_text: str) -> List[str]:
        return [
            token
            for token in pattern_text.split()
            if normalize_token(token) not in NAME_PARTICLES
        ]
