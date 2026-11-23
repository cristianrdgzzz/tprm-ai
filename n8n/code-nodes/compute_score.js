// n8n Code node: "compute_score"   (mode: Run Once for Each Item)
// Input : de-anonymized assessment JSON from the LLM
// Output: { ...assessment, scoring: {..., score_total, resultado, secciones}, db: {...} }
//
// The LLM is asked for per-control scores (1-5). Its own score_total/resultado
// were unreliable (often null or inconsistent), so the final score is computed
// here, deterministically, following the rules of prompts/prompt_tprm.txt:
//   - section score  = mean of non-null controls (null if >50% of controls are null)
//   - total (0-100)  = sum(section_mean * weight) * 20
//   - >=80 Aprobado | 60-79 Aprobado con condiciones | <60 Rechazado
//   - any null section -> "Evaluación incompleta"
//   - any gap with bloquea_aprobacion=true caps the result at "Rechazado"

const SECTIONS = {
  s1: { name: 'Seguridad de la información', weight: 0.30 },
  s2: { name: 'Gestión de accesos e identidades (IAM)', weight: 0.25 },
  s3: { name: 'Continuidad de negocio', weight: 0.15 },
  s4: { name: 'Protección de datos', weight: 0.20 },
  s5: { name: 'Seguridad en la nube', weight: 0.05 },
  s6: { name: 'Subcontratistas', weight: 0.05 },
};

// Fields inside `scoring` that are data, not 1-5 scores
const NON_SCORE_FIELDS = new Set([
  's3_rto_horas', 's3_rpo_horas', 's4_paises_transferencia', 'score_total', 'resultado',
]);

function toScore(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) && n >= 1 && n <= 5 ? n : null;
}

function computeScore(scoring = {}, gaps = []) {
  const secciones = {};
  let total = 0;
  let incomplete = false;

  for (const [prefix, meta] of Object.entries(SECTIONS)) {
    const keys = Object.keys(scoring).filter(
      (k) => k.startsWith(`${prefix}_`) && !NON_SCORE_FIELDS.has(k)
    );
    const values = keys.map((k) => toScore(scoring[k])).filter((v) => v !== null);
    const nullRatio = keys.length ? 1 - values.length / keys.length : 1;
    const mean = values.length && nullRatio <= 0.5
      ? values.reduce((a, b) => a + b, 0) / values.length
      : null;

    secciones[prefix] = {
      nombre: meta.name,
      peso: meta.weight,
      controles: keys.length,
      evaluados: values.length,
      media: mean === null ? null : Math.round(mean * 100) / 100,
    };
    if (mean === null) incomplete = true;
    else total += mean * meta.weight;
  }

  const blocking = (Array.isArray(gaps) ? gaps : []).filter(
    (g) => g && (g.bloquea_aprobacion === true || g.bloquea_aprobacion === 'true')
  );

  let score_total = incomplete ? null : Math.round(total * 20);
  let resultado;
  if (incomplete) resultado = 'Evaluación incompleta';
  else if (score_total >= 80) resultado = 'Aprobado';
  else if (score_total >= 60) resultado = 'Aprobado con condiciones';
  else resultado = 'Rechazado';

  if (blocking.length && resultado !== 'Evaluación incompleta') resultado = 'Rechazado';

  return { score_total, resultado, secciones, gaps_bloqueantes: blocking.length };
}

function firstCertExpiry(cert = {}) {
  return cert.iso_27001_hasta || cert.ens_hasta || cert.soc2_hasta || null;
}

function toDbParams(a) {
  const v = a.vendor || {};
  const s = a.scoring || {};
  const json = (x) => (x === undefined || x === null ? null : JSON.stringify(x));
  return {
    company_name: v.nombre,
    tipo_servicio: v.tipo_servicio ?? null,
    tier: v.tier ?? null,
    dpo_nombre: v.dpo_nombre ?? null,
    dpo_email: v.dpo_email ?? null,
    dpo_tipo: v.dpo_tipo ?? null,
    country: v.pais_servicio ?? null,
    localizacion_datos: v.localizacion_datos ?? null,
    subcontratistas: json(v.subcontratistas),
    certificaciones: json(a.certificaciones),
    cert_expiry: firstCertExpiry(a.certificaciones),
    scoring: json(s),
    gaps: json(a.gaps),
    campos_pendientes: json(a.campos_pendientes),
    overall_score: s.score_total ?? null,
    current_risk: s.resultado ?? null,
    summary: a.resumen_ejecutivo ?? null,
  };
}

function enrich(assessment, fallbackVendorName) {
  const a = JSON.parse(JSON.stringify(assessment || {}));
  a.vendor = a.vendor || {};
  if (!a.vendor.nombre && fallbackVendorName) a.vendor.nombre = fallbackVendorName;
  const result = computeScore(a.scoring || {}, a.gaps || []);
  a.scoring = {
    ...(a.scoring || {}),
    score_llm: a.scoring?.score_total ?? null,   // keep what the LLM said, for audit
    score_total: result.score_total,
    resultado: result.resultado,
    secciones: result.secciones,
  };
  a.db = toDbParams(a);
  return a;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { computeScore, enrich, toDbParams, SECTIONS };
}

// ---- n8n entry point -------------------------------------------------------
if (typeof $input !== 'undefined') {
  let fallback = null;
  try { fallback = $('extract_vendor').item.json.company_name; } catch (e) { /* optional */ }
  return { json: enrich($input.item.json, fallback) };
}
