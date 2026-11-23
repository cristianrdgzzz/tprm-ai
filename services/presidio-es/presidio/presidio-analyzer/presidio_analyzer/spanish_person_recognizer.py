"""Backward-compatible facade for the Spanish PERSON recognizer."""

from presidio_analyzer.spanish_enterprise.person_recognizer import (
    EsSpanishPersonRecognizer,
    SPANISH_PERSON_BLACKLIST,
)
from presidio_analyzer.spanish_enterprise.spacy_filters import (
    disable_spacy_person_for_spanish,
)

__all__ = [
    "EsSpanishPersonRecognizer",
    "SPANISH_PERSON_BLACKLIST",
    "disable_spacy_person_for_spanish",
]
