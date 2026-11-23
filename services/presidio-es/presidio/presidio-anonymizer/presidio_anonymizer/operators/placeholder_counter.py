"""Operator that replaces entities with structured placeholders and builds a mapping."""

from typing import Dict

from presidio_anonymizer.operators import Operator, OperatorType

CONTEXT_PREFIXES = (
    "certificado por ",
    "certificado ",
    "emitido por ",
    "auditado por ",
    "proveedor ",
    "empresa ",
)


class PlaceholderCounter(Operator):
    """
    Replaces each entity with a placeholder like <ENTITY_TYPE_001>.

    Builds a reverse mapping: {"PERSON_001": "Juan Pérez", ...}
    The full matched span is replaced in the output; mapping values store the
    clean entity name without leading context prefixes.
    """

    def operate(self, text: str, params: Dict = None) -> str:
        self.validate(params)
        entity_type = params["entity_type"]
        entity_mapping: Dict[str, str] = params["entity_mapping"]
        entity_counters: Dict[str, int] = params["entity_counters"]

        matched_text = text.strip()

        lowered = matched_text.lower()
        for prefix in CONTEXT_PREFIXES:
            if lowered.startswith(prefix):
                matched_text = matched_text[len(prefix) :]
                break

        mapping_value = matched_text.strip()

        for placeholder_key, original_value in entity_mapping.items():
            if (
                original_value == mapping_value
                and placeholder_key.startswith(f"{entity_type}_")
            ):
                return f"<{placeholder_key}>"

        count = entity_counters.get(entity_type, 0) + 1
        entity_counters[entity_type] = count
        placeholder_key = f"{entity_type}_{count:03d}"
        entity_mapping[placeholder_key] = mapping_value

        return f"<{placeholder_key}>"

    def validate(self, params: Dict = None) -> None:
        if "entity_mapping" not in params:
            raise ValueError("An input dict called `entity_mapping` is required.")
        if "entity_counters" not in params:
            raise ValueError("An input dict called `entity_counters` is required.")
        if "entity_type" not in params:
            raise ValueError("`entity_type` is required.")

    def operator_name(self) -> str:
        return "placeholder_counter"

    def operator_type(self) -> OperatorType:
        return OperatorType.Anonymize
