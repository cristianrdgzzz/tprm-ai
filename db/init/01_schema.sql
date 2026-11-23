-- TPRM-AI — PostgreSQL schema (database: tprm_ai)
-- Executed automatically by the postgres container on first start
-- (only when ./postgres is empty). n8n creates its own internal tables
-- in the same database; they do not collide with these.

-- ---------------------------------------------------------------------------
-- vendors: master record of each third party and its latest assessment
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vendors (
    id                  SERIAL PRIMARY KEY,
    company_name        TEXT NOT NULL UNIQUE,         -- UPSERT key
    cif                 TEXT,
    country             TEXT,
    tier                INTEGER,
    tipo_servicio       TEXT,
    current_risk        TEXT,                          -- Aprobado / Aprobado con condiciones / Rechazado / Evaluación incompleta
    overall_score       INTEGER CHECK (overall_score BETWEEN 0 AND 100),
    certifications      TEXT[],
    cert_expiry         DATE,
    certificaciones     JSONB,                         -- full certification block from the LLM
    dpo_nombre          TEXT,
    dpo_email           TEXT,
    dpo_tipo            TEXT,
    localizacion_datos  TEXT,
    subcontratistas     JSONB,
    scoring             JSONB,                         -- per-control scores (1-5) + computed totals
    gaps                JSONB,
    campos_pendientes   JSONB,
    summary             TEXT,                          -- executive summary
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- anonymized_documents: GDPR traceability — what was sent to the LLM and
-- the reversible mapping needed to restore it. The mapping never leaves
-- this database (not sent to the LLM, not vectorised into Qdrant).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS anonymized_documents (
    id               SERIAL PRIMARY KEY,
    vendor_id        INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
    file_name        TEXT NOT NULL,
    content_sha256   TEXT UNIQUE,                      -- sha256 of the anonymized text: same document is not stored twice
    anonymized_text  TEXT NOT NULL,
    entity_mapping   JSONB NOT NULL,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_anonymized_vendor ON anonymized_documents (vendor_id);

-- ---------------------------------------------------------------------------
-- Tables created for the next phases (not wired into the pipeline yet)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    vendor_id       INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
    document_type   TEXT,                              -- ISO cert, SOC2, DPA, BCP, pentest, questionnaire...
    file_name       TEXT,
    extracted_text  TEXT,
    ai_summary      TEXT,
    score           INTEGER,
    resultado       TEXT,
    processed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risks (
    id              SERIAL PRIMARY KEY,
    vendor_id       INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    severity        TEXT CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    blocks_approval BOOLEAN DEFAULT FALSE,
    status          TEXT DEFAULT 'open',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id              SERIAL PRIMARY KEY,
    vendor_id       INTEGER REFERENCES vendors(id) ON DELETE CASCADE,
    event_type      TEXT,                              -- cert_expiry, reassessment, contract_renewal
    event_date      DATE NOT NULL,
    description     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              SERIAL PRIMARY KEY,
    vendor_id       INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,
    details         JSONB,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Keep updated_at fresh on every UPDATE
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_vendors_updated_at ON vendors;
CREATE TRIGGER trg_vendors_updated_at
    BEFORE UPDATE ON vendors
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
