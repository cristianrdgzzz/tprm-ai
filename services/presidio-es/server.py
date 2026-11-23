"""
presidio-es — REST API for Spanish enterprise PII anonymization.

Wraps a modified Microsoft Presidio (see ./presidio) with Spanish recognizers
(COMPANY, PERSON, LOCATION, CIF/NIF/NIE, IBAN, phone, email) and a reversible
placeholder mapping, so vendor documents can be sent to an external LLM
without exposing personal or corporate data.

Endpoints
    GET  /health        liveness + loaded language
    POST /analyze       detected entities (debug / tuning)
    POST /anonymize     {anonymized_text, mapping}
    POST /deanonymize   restore placeholders in text or JSON using a mapping
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from fastapi import FastAPI, HTTPException
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import MappingAnonymizerEngine
from pydantic import BaseModel, Field

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("presidio-es")

LANGUAGE = os.getenv("PRESIDIO_LANGUAGE", "es")
SPACY_MODEL = os.getenv("SPACY_MODEL", "es_core_news_md")
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "500000"))

PLACEHOLDER_RE = re.compile(r"<([A-Z_]+_\d{3})>")

app = FastAPI(
    title="presidio-es",
    description="Spanish enterprise PII anonymization with reversible mapping (TPRM-AI)",
    version="1.1.0",
)

_nlp_engine = NlpEngineProvider(
    nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": LANGUAGE, "model_name": SPACY_MODEL}],
    }
).create_engine()
analyzer = AnalyzerEngine(nlp_engine=_nlp_engine, supported_languages=[LANGUAGE])
anonymizer = MappingAnonymizerEngine()
logger.info("Analyzer ready (language=%s, model=%s)", LANGUAGE, SPACY_MODEL)


class TextRequest(BaseModel):
    text: str = Field(..., description="Plain text extracted from a vendor document")
    language: str = Field(LANGUAGE, description="ISO language code")


class DeanonymizeRequest(BaseModel):
    data: Any = Field(..., description="String or JSON object containing <TYPE_NNN> placeholders")
    mapping: dict[str, str] = Field(..., description="Mapping returned by /anonymize")


def _check(req: TextRequest) -> None:
    if req.language != LANGUAGE:
        raise HTTPException(400, f"Only language '{LANGUAGE}' is loaded")
    if len(req.text) > MAX_TEXT_CHARS:
        raise HTTPException(413, f"Text exceeds {MAX_TEXT_CHARS} characters")


def restore(value: Any, mapping: dict[str, str]) -> Any:
    """Recursively replace <TYPE_NNN> placeholders with their original values."""
    if isinstance(value, str):
        return PLACEHOLDER_RE.sub(lambda m: mapping.get(m.group(1), m.group(0)), value)
    if isinstance(value, list):
        return [restore(v, mapping) for v in value]
    if isinstance(value, dict):
        return {k: restore(v, mapping) for k, v in value.items()}
    return value


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "language": LANGUAGE, "model": SPACY_MODEL}


@app.post("/analyze")
def analyze(req: TextRequest) -> dict[str, list[dict[str, Any]]]:
    _check(req)
    results = analyzer.analyze(text=req.text, language=req.language)
    return {
        "entities": [
            {
                "entity_type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": round(r.score, 3),
                "text": req.text[r.start : r.end],
            }
            for r in sorted(results, key=lambda r: r.start)
        ]
    }


@app.post("/anonymize")
def anonymize(req: TextRequest) -> dict[str, Any]:
    _check(req)
    try:
        results = analyzer.analyze(text=req.text, language=req.language)
        output = anonymizer.anonymize_with_mapping(text=req.text, analyzer_results=results)
        return {"anonymized_text": output.text, "mapping": output.mapping}
    except Exception as exc:  # surface errors to n8n instead of a bare 500
        logger.exception("Anonymization failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/deanonymize")
def deanonymize(req: DeanonymizeRequest) -> dict[str, Any]:
    return {"data": restore(req.data, req.mapping)}
