"""Spanish enterprise document recognizers for Presidio Analyzer."""

from presidio_analyzer.spanish_enterprise.company_recognizer import (
    EsSpanishCompanyRecognizer,
)
from presidio_analyzer.spanish_enterprise.organization_recognizer import (
    EsSpanishOrganizationRecognizer,
)
from presidio_analyzer.spanish_enterprise.location_recognizer import (
    EsSpanishLocationRecognizer,
)
from presidio_analyzer.spanish_enterprise.person_recognizer import (
    EsSpanishPersonRecognizer,
)
from presidio_analyzer.spanish_enterprise.registry import (
    get_spanish_enterprise_recognizers,
    register_spanish_enterprise_recognizers,
)
from presidio_analyzer.spanish_enterprise.spacy_filters import (
    disable_spacy_location_for_spanish,
    disable_spacy_organization_for_spanish,
    disable_spacy_person_for_spanish,
)

__all__ = [
    "EsSpanishCompanyRecognizer",
    "EsSpanishOrganizationRecognizer",
    "EsSpanishLocationRecognizer",
    "EsSpanishPersonRecognizer",
    "get_spanish_enterprise_recognizers",
    "register_spanish_enterprise_recognizers",
    "disable_spacy_person_for_spanish",
    "disable_spacy_location_for_spanish",
    "disable_spacy_organization_for_spanish",
]
