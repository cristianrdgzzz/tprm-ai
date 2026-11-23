"""Anonymizer root module."""

import logging

from .anonymizer_engine import AnonymizerEngine
from .batch_anonymizer_engine import BatchAnonymizerEngine
from .deanonymize_engine import DeanonymizeEngine
from .mapping_anonymizer_engine import MappingAnonymizerEngine
from .entities import (
    ConflictResolutionStrategy,
    DictRecognizerResult,
    EngineResult,
    InvalidParamError,
    MappingAnonymizerResult,
    OperatorConfig,
    OperatorResult,
    PIIEntity,
    RecognizerResult,
)

# Set up default logging (with NullHandler)


logging.getLogger("presidio-anonymizer").addHandler(logging.NullHandler())

__all__ = [
    "AnonymizerEngine",
    "MappingAnonymizerEngine",
    "DeanonymizeEngine",
    "BatchAnonymizerEngine",
    "InvalidParamError",
    "ConflictResolutionStrategy",
    "PIIEntity",
    "OperatorConfig",
    "OperatorResult",
    "RecognizerResult",
    "EngineResult",
    "MappingAnonymizerResult",
    "DictRecognizerResult",
]
