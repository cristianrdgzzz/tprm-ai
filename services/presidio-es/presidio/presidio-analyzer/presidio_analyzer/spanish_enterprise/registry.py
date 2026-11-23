"""Registration helpers for Spanish enterprise recognizers."""

from __future__ import annotations

from typing import List

from presidio_analyzer import EntityRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistry
from presidio_analyzer.spanish_enterprise.company_recognizer import (
    EsSpanishCompanyRecognizer,
)
from presidio_analyzer.spanish_enterprise.core_recognizers import (
    EsSpanishEmailRecognizer,
    EsSpanishIbanRecognizer,
    EsSpanishPhoneRecognizer,
    EsSpanishTaxIdRecognizer,
)
from presidio_analyzer.spanish_enterprise.location_recognizer import (
    EsSpanishLocationRecognizer,
)
from presidio_analyzer.spanish_enterprise.organization_recognizer import (
    EsSpanishOrganizationRecognizer,
)
from presidio_analyzer.spanish_enterprise.person_recognizer import (
    EsSpanishPersonRecognizer,
)
from presidio_analyzer.spanish_enterprise.spacy_filters import (
    disable_spacy_location_for_spanish,
    disable_spacy_organization_for_spanish,
    disable_spacy_person_for_spanish,
)


def get_spanish_enterprise_recognizers(
    supported_language: str = "es",
) -> List[EntityRecognizer]:
    """Return all Spanish enterprise recognizers for the given language."""
    return [
        EsSpanishTaxIdRecognizer(supported_language=supported_language),
        EsSpanishPhoneRecognizer(supported_language=supported_language),
        EsSpanishEmailRecognizer(supported_language=supported_language),
        EsSpanishIbanRecognizer(supported_language=supported_language),
        EsSpanishCompanyRecognizer(supported_language=supported_language),
        EsSpanishOrganizationRecognizer(supported_language=supported_language),
        EsSpanishPersonRecognizer(supported_language=supported_language),
        EsSpanishLocationRecognizer(supported_language=supported_language),
    ]


def register_spanish_enterprise_recognizers(
    registry: RecognizerRegistry,
    supported_language: str = "es",
) -> None:
    """Register Spanish enterprise recognizers and disable noisy spaCy entities."""
    disable_spacy_person_for_spanish(registry)
    disable_spacy_location_for_spanish(registry)
    disable_spacy_organization_for_spanish(registry)
    for recognizer in get_spanish_enterprise_recognizers(supported_language):
        registry.add_recognizer(recognizer)
