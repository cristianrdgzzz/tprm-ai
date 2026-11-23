import pytest

from presidio_anonymizer import MappingAnonymizerEngine
from presidio_anonymizer.entities import RecognizerResult
from presidio_anonymizer.tprm_anonymizer_utils import (
    deduplicate_overlapping,
    is_denylisted_span,
    prepare_analyzer_results,
)


def test_is_denylisted_span_rejects_technical_acronyms():
    assert is_denylisted_span("ISO")
    assert is_denylisted_span("MFA")
    assert is_denylisted_span("BCP")
    assert not is_denylisted_span("TechNova Solutions S.L.")


def test_prepare_analyzer_results_trims_and_deduplicates():
    text = "Subcontratistas en India y México"
    india_start = text.index("India")
    india_end = india_start + len("India")
    results = [
        RecognizerResult(
            entity_type="LOCATION", start=india_start, end=india_end, score=0.9
        ),
        RecognizerResult(
            entity_type="LOCATION", start=india_start, end=india_end + 10, score=0.5
        ),
    ]
    prepared = prepare_analyzer_results(text, results)
    assert len(prepared) == 1
    assert prepared[0].entity_type == "LOCATION"
    assert text[prepared[0].start : prepared[0].end] == "India"


def test_mapping_anonymizer_uses_clean_entity_text():
    text = "ISO MFA El Responsable es Juan Pérez y la empresa TechNova Solutions S.L."
    person_start = text.index("Juan Pérez")
    company_start = text.index("TechNova Solutions S.L.")
    analyzer_results = [
        RecognizerResult(entity_type="COMPANY", start=0, end=3, score=0.9),
        RecognizerResult(entity_type="COMPANY", start=4, end=7, score=0.9),
        RecognizerResult(
            entity_type="PERSON",
            start=person_start,
            end=person_start + len("Juan Pérez"),
            score=0.8,
        ),
        RecognizerResult(
            entity_type="COMPANY",
            start=company_start,
            end=company_start + len("TechNova Solutions S.L."),
            score=0.78,
        ),
    ]
    engine = MappingAnonymizerEngine()
    output = engine.anonymize_with_mapping(text=text, analyzer_results=analyzer_results)

    assert "<PERSON_001>" in output.text
    assert "<COMPANY_001>" in output.text
    assert output.mapping["PERSON_001"] == "Juan Pérez"
    assert output.mapping["COMPANY_001"] == "TechNova Solutions S.L."
    assert "ISO" not in output.mapping.values()
