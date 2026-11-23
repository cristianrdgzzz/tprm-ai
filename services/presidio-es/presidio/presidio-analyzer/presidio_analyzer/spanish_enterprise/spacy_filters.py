"""Disable noisy spaCy entity types for Spanish enterprise analysis."""

from __future__ import annotations

import logging

from presidio_analyzer.recognizer_registry import RecognizerRegistry

logger = logging.getLogger("presidio-analyzer")


def _disable_spacy_entities_for_spanish(
    registry: RecognizerRegistry,
    entities_to_disable: set[str],
) -> int:
    disabled_count = 0
    for recognizer in registry.recognizers:
        if recognizer.supported_language != "es":
            continue
        if recognizer.name != "SpacyRecognizer":
            continue

        if not set(recognizer.supported_entities).intersection(entities_to_disable):
            continue

        recognizer.supported_entities = [
            entity
            for entity in recognizer.supported_entities
            if entity not in entities_to_disable
        ]
        disabled_count += 1

    return disabled_count


def disable_spacy_person_for_spanish(registry: RecognizerRegistry) -> None:
    """Remove PERSON from Spanish spaCy recognizers."""
    disabled_count = _disable_spacy_entities_for_spanish(registry, {"PERSON"})
    if disabled_count:
        logger.info(
            "Disabled spaCy PERSON detection for Spanish in %s recognizer(s)",
            disabled_count,
        )


def disable_spacy_location_for_spanish(registry: RecognizerRegistry) -> None:
    """Remove LOCATION from Spanish spaCy recognizers."""
    disabled_count = _disable_spacy_entities_for_spanish(registry, {"LOCATION"})
    if disabled_count:
        logger.info(
            "Disabled spaCy LOCATION detection for Spanish in %s recognizer(s)",
            disabled_count,
        )


def disable_spacy_organization_for_spanish(registry: RecognizerRegistry) -> None:
    """Remove ORGANIZATION from Spanish spaCy recognizers."""
    disabled_count = _disable_spacy_entities_for_spanish(registry, {"ORGANIZATION"})
    if disabled_count:
        logger.info(
            "Disabled spaCy ORGANIZATION detection for Spanish in %s recognizer(s)",
            disabled_count,
        )
