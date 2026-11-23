# Changelog

## [1.1.0] — 2026-11
### Added
- Importable n8n workflow `TPRM_Pipeline.json`, generated from the tested Code nodes and SQL (`scripts/build_workflow.py`)
- Processed PDFs are moved to `n8n-files/processed/`; OpenRouter call retries on failure
- Real pipeline output in `samples/output/` and a "Results" section showing why scoring is computed in code
- Deterministic weighted scoring with blocking gaps (`compute_score.js`) + unit tests
- Main-vendor detection that ignores certification bodies (`extract_vendor.js`)
- Idempotent storage of anonymized documents (`content_sha256`)
- `/analyze` and `/deanonymize` endpoints in presidio-es
- OCR of multi-page scanned PDFs (pdf2image) with Spanish language pack
- PostgreSQL schema as code (`db/init`), scripts (health, export/import workflows, Qdrant init)
- Documentation, diagrams and CI

### Fixed
- COMPANY recognizer swallowed the words before the company name ("El proveedor TechNova Solutions S.L"),
  which made the vendor name leak un-anonymized when it overlapped other entities. Regression test added.

### Changed
- Secrets moved from `docker-compose.yml` to `.env`; ports bound to `127.0.0.1`
- Repository reorganised into `services/`, `n8n/`, `db/`, `docs/`
- Presidio fork trimmed to the two packages actually used (analyzer + anonymizer)

## [1.0.0] — 2026-07
- End-to-end pipeline: ingestion → OCR → Spanish anonymization → LLM assessment → de-anonymization → PostgreSQL → CSV
- RAG infrastructure (Qdrant collections + local embeddings)
