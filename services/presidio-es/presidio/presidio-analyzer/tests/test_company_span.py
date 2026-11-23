"""Regression: COMPANY spans must not swallow the words that precede the name."""

import pytest
from presidio_analyzer.spanish_enterprise.company_recognizer import EsSpanishCompanyRecognizer


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Certificado emitido a TechNova Solutions S.L. (CIF B12345678).", "TechNova Solutions S.L"),
        ("El proveedor TechNova Solutions S.L. presta servicios.", "TechNova Solutions S.L"),
        ("Grupo Alfa Beta S.A.U. firma el contrato.", "Grupo Alfa Beta S.A.U"),
    ],
)
def test_company_span_starts_at_the_name(text, expected):
    results = EsSpanishCompanyRecognizer().analyze(text, ["COMPANY"])
    spans = [text[r.start : r.end] for r in results]
    assert expected in spans


def test_company_ignores_acronyms_before_suffix():
    text = "la empresa cumple ISO 27001 con MFA S.A."
    assert EsSpanishCompanyRecognizer().analyze(text, ["COMPANY"]) == []
