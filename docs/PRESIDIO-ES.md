# presidio-es — Spanish enterprise anonymization

A FastAPI service ([`services/presidio-es/server.py`](../services/presidio-es/server.py)) on top of a modified copy of Microsoft Presidio (`services/presidio-es/presidio/`).

## What was changed in Presidio

| Area | File(s) | Change |
|---|---|---|
| Analyzer engine | `presidio_analyzer/analyzer_engine.py` | Auto-registers the Spanish enterprise recognizers when `es` is a supported language |
| Recognizers | `presidio_analyzer/spanish_enterprise/` | `EsSpanishCompanyRecognizer`, `EsSpanishOrganizationRecognizer`, `EsSpanishPersonRecognizer`, `EsSpanishLocationRecognizer`, tax ID (CIF/NIF/NIE), IBAN, phone, email |
| spaCy filters | `spanish_enterprise/spacy_filters.py` | Disables the noisy default spaCy PERSON / LOCATION / ORG entities for Spanish |
| Anonymizer | `presidio_anonymizer/mapping_anonymizer_engine.py` | `MappingAnonymizerEngine.anonymize_with_mapping()` → text + flat reversible mapping |
| Operator | `presidio_anonymizer/operators/placeholder_counter.py` | `<TYPE_NNN>` placeholders with per-type counters |
| Pre-processing | `presidio_anonymizer/tprm_anonymizer_utils.py` | corrupt-span filter → TPRM acronym denylist → overlap de-duplication |
| Tests | `presidio-analyzer/tests/test_spanish_enterprise_recognizers.py`, `presidio-anonymizer/tests/test_tprm_mapping_anonymizer.py` | Unit tests for the above |

## Recognizer notes

- **COMPANY (legal entity):** requires a Spanish legal suffix (S.L., S.A., S.L.U., S.A.U.), title-case tokens, and rejects acronyms and certificate-number patterns such as `ES-SI-27001-45879`.
- **COMPANY (organisation / certifier):** multi-token names like *SGS ICS Iberia*, only with context (`require_context=True`, base score 0.0 → 0.75 with context); strips prefixes like *"Certificado por"*.
- **Entity aliases:** `EMAIL_ADDRESS→EMAIL`, `PHONE_NUMBER→PHONE`, `ES_NIF/ES_NIE→CIF`, `IBAN_CODE→IBAN`, `ORGANIZATION/ORG→COMPANY`.

## Usage

```bash
curl -s localhost:5002/anonymize -H 'Content-Type: application/json' \
  -d '{"text":"Empresa: TechNova Solutions S.L. Contacto: dpo@technova.eu"}'
# {"anonymized_text":"Empresa: <COMPANY_001>. Contacto: <EMAIL_001>",
#  "mapping":{"COMPANY_001":"TechNova Solutions S.L","EMAIL_001":"dpo@technova.eu"}}
```

Edit recognizers live: the source is mounted as a volume, so `docker compose restart presidio-anonymizer` is enough.

## Known limitations

Tested against the real service (Nov 2026):

- `PERSON` is the weak spot: some names are missed or typed as `COMPANY` (e.g. a DPO name after "DPO:"). They are still replaced by a placeholder when typed as `COMPANY`, but not always detected. 5 of the 22 original recognizer tests (PERSON / LOCATION / ORGANIZATION) fail and are tracked as non-blocking in CI.
- Synthetic CIFs with an invalid check digit are not detected (real CIFs are validated).
- When a context word is part of a matched span (e.g. "emitido por SGS ICS Iberia"), the whole span is replaced but the mapping stores only the clean name, so de-anonymization is not byte-identical to the original text.
- Certificate numbers are intentionally not anonymized yet.
- Only Spanish (`es`) is loaded.
