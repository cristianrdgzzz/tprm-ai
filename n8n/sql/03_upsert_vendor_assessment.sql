-- Branch B (assessment): store the de-anonymized LLM evaluation.
-- COALESCE keeps existing good data when the new document does not mention a field.
-- Query Parameters come from the compute_score node output ($json.db):
--   $1 company_name  $2 tipo_servicio  $3 tier  $4 dpo_nombre  $5 dpo_email
--   $6 dpo_tipo      $7 country        $8 localizacion_datos
--   $9 subcontratistas (json)  $10 certificaciones (json)  $11 cert_expiry (DD/MM/YYYY)
--   $12 scoring (json)  $13 gaps (json)  $14 campos_pendientes (json)
--   $15 overall_score  $16 current_risk  $17 summary
INSERT INTO vendors (
    company_name, tipo_servicio, tier, dpo_nombre, dpo_email, dpo_tipo, country,
    localizacion_datos, subcontratistas, certificaciones, cert_expiry,
    scoring, gaps, campos_pendientes, overall_score, current_risk, summary
)
VALUES (
    $1, $2, NULLIF($3, '')::int, $4, $5, $6, $7,
    $8, $9::jsonb, $10::jsonb, TO_DATE(NULLIF($11, ''), 'DD/MM/YYYY'),
    $12::jsonb, $13::jsonb, $14::jsonb, NULLIF($15, '')::int, $16, $17
)
ON CONFLICT (company_name) DO UPDATE SET
    tipo_servicio      = COALESCE(EXCLUDED.tipo_servicio,      vendors.tipo_servicio),
    tier               = COALESCE(EXCLUDED.tier,               vendors.tier),
    dpo_nombre         = COALESCE(EXCLUDED.dpo_nombre,         vendors.dpo_nombre),
    dpo_email          = COALESCE(EXCLUDED.dpo_email,          vendors.dpo_email),
    dpo_tipo           = COALESCE(EXCLUDED.dpo_tipo,           vendors.dpo_tipo),
    country            = COALESCE(EXCLUDED.country,            vendors.country),
    localizacion_datos = COALESCE(EXCLUDED.localizacion_datos, vendors.localizacion_datos),
    subcontratistas    = COALESCE(EXCLUDED.subcontratistas,    vendors.subcontratistas),
    certificaciones    = COALESCE(EXCLUDED.certificaciones,    vendors.certificaciones),
    cert_expiry        = COALESCE(EXCLUDED.cert_expiry,        vendors.cert_expiry),
    scoring            = COALESCE(EXCLUDED.scoring,            vendors.scoring),
    gaps               = COALESCE(EXCLUDED.gaps,               vendors.gaps),
    campos_pendientes  = COALESCE(EXCLUDED.campos_pendientes,  vendors.campos_pendientes),
    overall_score      = COALESCE(EXCLUDED.overall_score,      vendors.overall_score),
    current_risk       = COALESCE(EXCLUDED.current_risk,       vendors.current_risk),
    summary            = COALESCE(EXCLUDED.summary,            vendors.summary)
RETURNING id;
