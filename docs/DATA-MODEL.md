# Data model

Schema: [`db/init/01_schema.sql`](../db/init/01_schema.sql) — applied automatically the first time the PostgreSQL volume is created.

```mermaid
erDiagram
    vendors ||--o{ anonymized_documents : "has"
    vendors ||--o{ documents : "has"
    vendors ||--o{ risks : "has"
    vendors ||--o{ calendar_events : "has"
    vendors ||--o{ audit_log : "has"

    vendors {
        serial id PK
        text company_name UK "UPSERT key"
        int tier
        text tipo_servicio
        text current_risk "Aprobado / Rechazado / ..."
        int overall_score "0-100, computed in code"
        date cert_expiry
        jsonb certificaciones
        text dpo_nombre
        text dpo_email
        text localizacion_datos
        jsonb subcontratistas
        jsonb scoring "per-control 1-5 + sections"
        jsonb gaps
        jsonb campos_pendientes
        text summary
        timestamp updated_at
    }
    anonymized_documents {
        serial id PK
        int vendor_id FK
        text file_name
        text content_sha256 UK "idempotency"
        text anonymized_text
        jsonb entity_mapping "never leaves the DB"
        timestamp created_at
    }
    documents {
        serial id PK
        int vendor_id FK
        text document_type
        int score
    }
    risks {
        serial id PK
        int vendor_id FK
        text severity
        bool blocks_approval
    }
    calendar_events {
        serial id PK
        int vendor_id FK
        text event_type
        date event_date
    }
    audit_log {
        serial id PK
        int vendor_id FK
        text action
        jsonb details
    }
```

| Table | Status |
|---|---|
| `vendors` | ✅ used by the pipeline |
| `anonymized_documents` | ✅ used by the pipeline |
| `documents`, `risks`, `calendar_events`, `audit_log` | 🗺️ created for the next phases |

n8n creates its own internal tables (`execution_*`, `workflow_*`, …) in the same database.

## Qdrant collections (RAG, in progress)

| Collection | Vector | Payload |
|---|---|---|
| `vendors_docs` | 1024, cosine | `vendor_id, document_id, file_name, chunk_index, chunk_text` |
| `vendors_assessments` | 1024, cosine | `vendor_id, tier, score, assessment_text` |
