# presidio-es

FastAPI wrapper around a modified Microsoft Presidio for Spanish enterprise documents.
See [`docs/PRESIDIO-ES.md`](../../docs/PRESIDIO-ES.md) for what was changed and why.

```
presidio-es/
├── Dockerfile
├── server.py                 # /health /analyze /anonymize /deanonymize
└── presidio/
    ├── presidio-analyzer/    # fork: spanish_enterprise/ recognizers
    └── presidio-anonymizer/  # fork: MappingAnonymizerEngine, PlaceholderCounter
```

Run the custom unit tests locally:

```bash
pip install -e presidio/presidio-analyzer -e presidio/presidio-anonymizer pytest
python -m spacy download es_core_news_md
cd presidio
pytest presidio-analyzer/tests/test_company_span.py presidio-analyzer/tests/test_spanish_enterprise_recognizers.py
pytest presidio-anonymizer/tests/test_tprm_mapping_anonymizer.py   # run separately (conftest clash)
```

The Presidio packages are © Microsoft Corporation, MIT License (see `presidio/LICENSE`).
