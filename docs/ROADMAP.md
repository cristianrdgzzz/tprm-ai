# Roadmap

## ✅ Done
- Local stack in Docker Compose (n8n, PostgreSQL, Qdrant, presidio-es, ocr-api)
- OCR fallback for scanned PDFs
- Spanish enterprise anonymization with reversible mapping (Presidio fork)
- LLM assessment on anonymized text only; local de-anonymization
- PostgreSQL persistence with `UPSERT … COALESCE`; GDPR evidence table
- Vendor inventory CSV
- Deterministic weighted scoring + blocking gaps (tested)
- Main-vendor detection ignoring certification bodies (tested)
- Idempotent document storage (content hash)
- Secrets moved to `.env`; ports bound to localhost
- RAG infrastructure: embeddings service + Qdrant collections

## 🚧 In progress
- RAG backfill of anonymized documents into `vendors_docs`
- RAG ingestion of past assessments into `vendors_assessments`

## 🗺️ Next
1. Retrieval in the main pipeline (history + current vendor state in the prompt)
2. Better `PERSON` recognition; anonymize certificate numbers
3. Few-shot examples in the prompt
4. `risks`, `audit_log` and certificate-expiry `calendar_events` populated by the pipeline
5. Per-vendor report (Excel/PDF) and a lightweight dashboard
6. Optional fully-local LLM profile (Ollama)
7. Map findings to NIS2 / DORA ICT third-party requirements
