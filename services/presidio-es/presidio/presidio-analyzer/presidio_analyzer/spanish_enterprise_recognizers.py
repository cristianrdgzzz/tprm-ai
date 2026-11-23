"""Backward-compatible facade for Spanish enterprise recognizers."""

from presidio_analyzer.spanish_enterprise import (
    EsSpanishCompanyRecognizer,
    EsSpanishLocationRecognizer,
    EsSpanishPersonRecognizer,
    disable_spacy_location_for_spanish,
    disable_spacy_person_for_spanish,
    get_spanish_enterprise_recognizers,
    register_spanish_enterprise_recognizers,
)
from presidio_analyzer.spanish_enterprise.core_recognizers import (
    EsSpanishEmailRecognizer,
    EsSpanishIbanRecognizer,
    EsSpanishPhoneRecognizer,
    EsSpanishTaxIdRecognizer,
)

__all__ = [
    "EsSpanishTaxIdRecognizer",
    "EsSpanishPhoneRecognizer",
    "EsSpanishEmailRecognizer",
    "EsSpanishIbanRecognizer",
    "EsSpanishCompanyRecognizer",
    "EsSpanishPersonRecognizer",
    "EsSpanishLocationRecognizer",
    "get_spanish_enterprise_recognizers",
    "register_spanish_enterprise_recognizers",
    "disable_spacy_person_for_spanish",
    "disable_spacy_location_for_spanish",
]
