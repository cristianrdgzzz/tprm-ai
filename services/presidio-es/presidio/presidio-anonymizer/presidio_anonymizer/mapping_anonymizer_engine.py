"""Anonymizer engine that returns structured placeholders and a reversible mapping."""

from typing import Dict, List, Optional, Set

from presidio_anonymizer.anonymizer_engine import AnonymizerEngine
from presidio_anonymizer.entities import (
    ConflictResolutionStrategy,
    EngineResult,
    MappingAnonymizerResult,
    OperatorConfig,
    RecognizerResult,
)
from presidio_anonymizer.operators.placeholder_counter import PlaceholderCounter
from presidio_anonymizer.tprm_anonymizer_utils import (
    TPRM_TECHNICAL_DENYLIST,
    get_span_text,
    prepare_analyzer_results,
)

DEFAULT_ENTITY_TYPE_ALIASES = {
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "ES_NIF": "CIF",
    "ES_NIE": "CIF",
    "IBAN_CODE": "IBAN",
    "ORGANIZATION": "COMPANY",
    "ORG": "COMPANY",
}


class MappingAnonymizerEngine(AnonymizerEngine):
    """
    Presidio anonymizer that replaces entities with structured placeholders.

    Returns both anonymized text and a flat mapping dictionary, e.g.::

        {
            "PERSON_001": "Juan Pérez",
            "EMAIL_001": "juan@gmail.com"
        }
    """

    def __init__(self):
        super().__init__()
        self.add_anonymizer(PlaceholderCounter)

    def anonymize_with_mapping(
        self,
        text: str,
        analyzer_results: List[RecognizerResult],
        entity_type_aliases: Optional[Dict[str, str]] = None,
        operators: Optional[Dict[str, OperatorConfig]] = None,
        denylist: Optional[Set[str]] = None,
        conflict_resolution: ConflictResolutionStrategy = (
            ConflictResolutionStrategy.REMOVE_INTERSECTIONS
        ),
        merge_entities_with_spaces: bool = False,
    ) -> MappingAnonymizerResult:
        """
        Anonymize text and return both the anonymized text and entity mapping.

        Entities are sanitized, denylisted acronyms removed, overlapping spans
        deduplicated (highest score wins), then replaced end-to-start.
        """
        aliases = {**DEFAULT_ENTITY_TYPE_ALIASES, **(entity_type_aliases or {})}
        denylist = denylist or set(TPRM_TECHNICAL_DENYLIST)

        prepared_results = prepare_analyzer_results(
            text=text,
            analyzer_results=analyzer_results,
            denylist=denylist,
        )
        normalized_results = self._normalize_entity_types(prepared_results, aliases)

        entity_mapping: Dict[str, str] = {}
        entity_counters: Dict[str, int] = {}
        placeholder_params = {
            "entity_mapping": entity_mapping,
            "entity_counters": entity_counters,
            "source_text": text,
        }

        if operators:
            resolved_operators = dict(operators)
            if "DEFAULT" not in resolved_operators:
                resolved_operators["DEFAULT"] = OperatorConfig(
                    "placeholder_counter", placeholder_params
                )
            for entity_type, operator_config in list(resolved_operators.items()):
                if entity_type == "DEFAULT":
                    continue
                if operator_config.operator_name == "placeholder_counter":
                    resolved_operators[entity_type] = OperatorConfig(
                        "placeholder_counter", placeholder_params
                    )
        else:
            resolved_operators = {
                "DEFAULT": OperatorConfig("placeholder_counter", placeholder_params)
            }

        engine_result: EngineResult = self.anonymize(
            text=text,
            analyzer_results=normalized_results,
            operators=resolved_operators,
            conflict_resolution=conflict_resolution,
            merge_entities_with_spaces=merge_entities_with_spaces,
        )
        return MappingAnonymizerResult.from_engine_result(engine_result, entity_mapping)

    @staticmethod
    def _normalize_entity_types(
        analyzer_results: List[RecognizerResult],
        aliases: Dict[str, str],
    ) -> List[RecognizerResult]:
        normalized_results = []
        for result in analyzer_results:
            normalized_results.append(
                RecognizerResult(
                    start=result.start,
                    end=result.end,
                    entity_type=aliases.get(result.entity_type, result.entity_type),
                    score=result.score,
                )
            )
        return normalized_results
