"""Anonymizer result that includes a reversible entity mapping."""

import json
from dataclasses import dataclass, field
from typing import Dict, List

from presidio_anonymizer.entities.engine.result.engine_result import EngineResult
from presidio_anonymizer.entities.engine.result.operator_result import OperatorResult


@dataclass
class MappingAnonymizerResult:
    """Anonymized text plus a flat placeholder-to-original mapping."""

    text: str
    mapping: Dict[str, str] = field(default_factory=dict)
    items: List[OperatorResult] = field(default_factory=list)

    @classmethod
    def from_engine_result(
        cls,
        engine_result: EngineResult,
        mapping: Dict[str, str],
    ) -> "MappingAnonymizerResult":
        return cls(
            text=engine_result.text,
            mapping=dict(mapping),
            items=list(engine_result.items),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "anonymized_text": self.text,
            "mapping": self.mapping,
            "items": [item.__dict__ for item in self.items],
        }

    def to_json(self) -> str:
        """Serialize the result for storage (e.g. PostgreSQL JSONB)."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
