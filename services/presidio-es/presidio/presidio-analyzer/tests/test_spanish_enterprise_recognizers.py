import pytest

from presidio_analyzer import PatternRecognizer, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_analyzer.spanish_enterprise.company_recognizer import (
    EsSpanishCompanyRecognizer,
)
from presidio_analyzer.spanish_enterprise.location_recognizer import (
    EsSpanishLocationRecognizer,
)
from presidio_analyzer.spanish_enterprise.person_recognizer import (
    EsSpanishPersonRecognizer,
)
from presidio_analyzer.spanish_enterprise.organization_recognizer import (
    EsSpanishOrganizationRecognizer,
)
from presidio_analyzer.spanish_enterprise.spacy_filters import (
    disable_spacy_location_for_spanish,
    disable_spacy_organization_for_spanish,
    disable_spacy_person_for_spanish,
)
from presidio_analyzer.spanish_enterprise.utils import normalize_enterprise_text


@pytest.fixture
def person_recognizer():
    return EsSpanishPersonRecognizer()


@pytest.fixture
def company_recognizer():
    return EsSpanishCompanyRecognizer()


@pytest.fixture
def location_recognizer():
    return EsSpanishLocationRecognizer()


def test_normalize_enterprise_text_collapses_whitespace_and_ocr():
    text = "Contacto:\u00a0Juan\u200b  Pérez"
    normalized = normalize_enterprise_text(text)
    assert normalized == "Contacto: Juan Pérez"


@pytest.mark.parametrize(
    "text,expected_score",
    [
        ("El Responsable de protección es Juan Pérez.", 0.8),
        ("Juan Pérez firmó el documento.", 0.4),
    ],
)
def test_spanish_person_fallback_scoring(person_recognizer, text, expected_score):
    results = person_recognizer.analyze(text=text, entities=["PERSON"])
    assert results
    assert results[0].score == expected_score


@pytest.mark.parametrize(
    "text,should_match",
    [
        ("El Responsable de protección es Juan Pérez.", True),
        ("Operaciones en India y México para el cliente.", False),
        ("India y México", False),
    ],
)
def test_spanish_person_rejects_conjunctions_and_countries(
    person_recognizer, text, should_match
):
    results = person_recognizer.analyze(text=text, entities=["PERSON"])
    assert bool(results) is should_match


@pytest.mark.parametrize(
    "text,should_match",
    [
        ("El proveedor Consultores Ibérica S.L. entregará el servicio.", True),
        ("La empresa Innovación Digital S.A.U. cumple el requisito.", True),
        ("ISO MFA RPO BCP SaaS SA", False),
        ("Proveedor SaaS SA", False),
        ("La empresa TechNova Solutions S.L. presta el servicio.", True),
        ("GDPR", False),
        ("SLA", False),
    ],
)
def test_spanish_company_recognizer(company_recognizer, text, should_match):
    results = company_recognizer.analyze(text=text, entities=["COMPANY"])
    assert bool(results) is should_match
    if results:
        assert results[0].score >= 0.45


@pytest.mark.parametrize(
    "text,should_match",
    [
        ("La sede principal está en Madrid.", True),
        ("Operamos en España, México e India.", True),
        ("La oficina está en Portugal.", True),
        ("Los controles de seguridad en infraestructura", False),
        ("Se aplican medidas en Cloud Security", False),
        ("India y México", False),
        ("Operaciones con Acme Solutions Group", False),
    ],
)
def test_spanish_location_recognizer(location_recognizer, text, should_match):
    results = location_recognizer.analyze(text=text, entities=["LOCATION"])
    assert bool(results) is should_match


def test_spanish_organization_recognizer():
    recognizer = EsSpanishOrganizationRecognizer()
    text = "Certificador externo SGS ICS Iberia emitió el informe."
    results = recognizer.analyze(text=text, entities=["COMPANY"])
    assert results
    assert "SGS ICS Iberia" in text[results[0].start : results[0].end]


def test_disable_spacy_entities_for_spanish():
    registry = RecognizerRegistry(
        recognizers=[
            SpacyRecognizer(
                supported_language="es",
                supported_entities=["PERSON", "LOCATION", "ORGANIZATION"],
            ),
            PatternRecognizer(
                supported_entity="EMAIL",
                patterns=[],
                deny_list=["test@example.com"],
                supported_language="es",
            ),
        ]
    )

    disable_spacy_person_for_spanish(registry)
    disable_spacy_location_for_spanish(registry)
    disable_spacy_organization_for_spanish(registry)

    spacy_recognizer = registry.recognizers[0]
    assert "PERSON" not in spacy_recognizer.supported_entities
    assert "LOCATION" not in spacy_recognizer.supported_entities
    assert "ORGANIZATION" not in spacy_recognizer.supported_entities
