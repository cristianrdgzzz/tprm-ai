"""Spanish LOCATION recognizer with allowlist and document-term filtering."""

from __future__ import annotations

from typing import FrozenSet, List, Optional, Set

from presidio_analyzer import Pattern
from presidio_analyzer.spanish_enterprise.base import SpanishEnterprisePatternRecognizer
from presidio_analyzer.spanish_enterprise.utils import (
    EntityScore,
    contains_blacklisted_token,
    contains_conjunction,
    is_acronym_token,
    is_title_case_token,
    normalize_token,
)

LOCATION_BLACKLIST: FrozenSet[str] = frozenset(
    {
        "controles",
        "seguridad",
        "infraestructura",
        "saas",
        "actividad",
        "empresa",
        "servicio",
        "proveedor",
        "gestión",
        "gestion",
        "análisis",
        "analisis",
        "documento",
        "informe",
        "proceso",
        "sistema",
        "software",
        "datos",
        "personal",
        "cumplimiento",
        "auditoría",
        "auditoria",
        "riesgo",
        "medida",
        "requisito",
        "contrato",
        "acuerdo",
        "política",
        "politica",
        "iso",
        "mfa",
        "rto",
        "bcp",
    }
)

ORGANIZATION_LIKE_TERMS: FrozenSet[str] = frozenset(
    {
        "solutions",
        "solution",
        "group",
        "ics",
        "systems",
        "system",
        "services",
        "service",
        "consulting",
        "technologies",
        "technology",
        "partners",
        "partner",
        "holdings",
        "corp",
        "inc",
        "ltd",
        "gmbh",
    }
)

LOCATION_CONTEXT_TERMS: tuple[str, ...] = (
    "ubicado",
    "ubicada",
    "sede",
    "oficina",
    "país",
    "pais",
    "ciudad",
    "localización",
    "localizacion",
    "provincia",
    "comunidad",
    "dirección",
    "direccion",
)

KNOWN_LOCATIONS: FrozenSet[str] = frozenset(
    {
        "españa",
        "espana",
        "spain",
        "méxico",
        "mexico",
        "india",
        "portugal",
        "francia",
        "alemania",
        "irlanda",
        "madrid",
        "barcelona",
        "valencia",
        "sevilla",
        "zaragoza",
        "málaga",
        "malaga",
        "murcia",
        "palma",
        "bilbao",
        "alicante",
        "córdoba",
        "cordoba",
        "valladolid",
        "vigo",
        "gijón",
        "gijon",
        "hospitalet",
        "vitoria",
        "granada",
        "elche",
        "oviedo",
        "badalona",
        "cartagena",
        "terrassa",
        "jerez",
        "sabadell",
        "móstoles",
        "mostoles",
        "santa cruz de tenerife",
        "pamplona",
        "almería",
        "almeria",
        "león",
        "leon",
        "castellón",
        "castellon",
        "cádiz",
        "cadiz",
        "burgos",
        "salamanca",
        "albacete",
        "logroño",
        "logrono",
        "huelva",
        "marbella",
        "lugo",
        "tarragona",
        "jaén",
        "jaen",
        "ourense",
        "girona",
        "cáceres",
        "caceres",
        "toledo",
        "ceuta",
        "melilla",
        "europa",
        "europe",
        "cataluña",
        "cataluna",
        "andalucía",
        "andalucia",
        "galicia",
        "aragon",
        "aragón",
        "castilla",
        "extremadura",
        "navarra",
        "asturias",
        "cantabria",
        "rioja",
        "baleares",
        "canarias",
    }
)

_LOCATION_TOKEN = (
    r"[A-ZÁÉÍÓÚÑÜ][A-Za-zÁÉÍÓÚÑÜáéíóúñü]{3,}"
    r"(?:\s+(?:de|del|la|los|las)\s+[A-ZÁÉÍÓÚÑÜ][A-Za-zÁÉÍÓÚÑÜáéíóúñü]{3,})?"
)


class EsSpanishLocationRecognizer(SpanishEnterprisePatternRecognizer):
    """Detect geographic locations while rejecting enterprise document vocabulary."""

    COUNTRY_CODE = "es"

    PATTERNS = [
        Pattern("Known location token", rf"\b{_LOCATION_TOKEN}\b", 0.4),
        Pattern(
            "Known multi-word location",
            rf"\b{_LOCATION_TOKEN}(?:\s+{_LOCATION_TOKEN}){{0,1}}\b",
            0.4,
        ),
    ]

    CONTEXT = list(LOCATION_CONTEXT_TERMS)
    MIN_TOKEN_LENGTH = 4

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "es",
        supported_entity: str = "LOCATION",
        blacklist: Optional[Set[str]] = None,
        known_locations: Optional[Set[str]] = None,
        name: Optional[str] = None,
    ):
        self.known_locations = (
            set(known_locations) if known_locations is not None else set(KNOWN_LOCATIONS)
        )
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns or self.PATTERNS,
            context=context or self.CONTEXT,
            supported_language=supported_language,
            blacklist=set(blacklist) if blacklist is not None else set(LOCATION_BLACKLIST),
            context_boost_terms=set(LOCATION_CONTEXT_TERMS),
            entity_score=EntityScore(base=0.42, with_context=0.76, without_context=0.42),
            require_context=False,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        if contains_conjunction(pattern_text):
            return False
        if contains_blacklisted_token(pattern_text, self.blacklist):
            return False
        if self._contains_organization_like_term(pattern_text):
            return False

        tokens = [token for token in pattern_text.split() if token]
        if not tokens:
            return False

        if all(is_acronym_token(token) for token in tokens):
            return False

        known_token_hits = [
            token
            for token in tokens
            if normalize_token(token) in self.known_locations
        ]
        if not known_token_hits:
            return False

        for token in tokens:
            normalized = normalize_token(token)
            if normalized in self.blacklist:
                return False
            if len(normalized) < self.MIN_TOKEN_LENGTH:
                return False
            if not is_title_case_token(token, min_length=self.MIN_TOKEN_LENGTH):
                return False

        return True

    @staticmethod
    def _contains_organization_like_term(pattern_text: str) -> bool:
        for token in pattern_text.split():
            normalized = normalize_token(token)
            if normalized in ORGANIZATION_LIKE_TERMS:
                return True
            if normalized.endswith("ics") and normalized not in KNOWN_LOCATIONS:
                return True
        return False
