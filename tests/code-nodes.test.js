// Unit tests for the n8n Code nodes.  Run: node --test tests/
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { pickVendor, sha256 } = require('../n8n/code-nodes/extract_vendor.js');
const { buildBody, MARKER } = require('../n8n/code-nodes/build_prompt.js');
const { extractJson } = require('../n8n/code-nodes/clean_llm_json.js');
const { restore } = require('../n8n/code-nodes/deanonymize.js');
const { computeScore, enrich } = require('../n8n/code-nodes/compute_score.js');

const sample = JSON.parse(
  fs.readFileSync(path.join(__dirname, '../samples/anonymization_example.json'), 'utf8')
);

test('extract_vendor skips certification bodies and prefers the legal entity', () => {
  const v = pickVendor(sample.output.anonymized_text, sample.output.mapping);
  assert.equal(v.value, 'TechNova Solutions S.L');
});

test('extract_vendor returns null when there are no companies', () => {
  assert.equal(pickVendor('texto', { EMAIL_001: 'a@b.com' }), null);
});

test('sha256 is deterministic', () => {
  assert.equal(sha256('abc'), sha256('abc'));
  assert.notEqual(sha256('abc'), sha256('abd'));
});

test('build_prompt puts only the anonymized document in the user message', () => {
  const tpl = fs.readFileSync(path.join(__dirname, '../n8n-files/maestro/prompt_tprm.txt'), 'utf8');
  const body = buildBody(tpl, 'Proveedor <COMPANY_001>', 'test-model');
  assert.equal(body.model, 'test-model');
  assert.equal(body.messages[0].role, 'system');
  assert.ok(!body.messages[0].content.includes(MARKER));
  assert.ok(body.messages[0].content.includes('"scoring"'));
  assert.ok(body.messages[1].content.endsWith('Proveedor <COMPANY_001>'));
});

test('build_prompt fails if the marker is missing', () => {
  assert.throws(() => buildBody('sin marcador', 'x'));
});

test('clean_llm_json strips markdown fences and chatter', () => {
  assert.deepEqual(extractJson('Aquí tienes:\n```json\n{"a": 1}\n```'), { a: 1 });
  assert.throws(() => extractJson('no json here'));
});

test('deanonymize restores nested placeholders and keeps unknown ones', () => {
  const out = restore(
    { vendor: { nombre: '<COMPANY_002>', subs: ['<LOCATION_001>', '<X_009>'] }, n: 3 },
    sample.output.mapping
  );
  assert.equal(out.vendor.nombre, 'TechNova Solutions S.L');
  assert.deepEqual(out.vendor.subs, ['India', '<X_009>']);
  assert.equal(out.n, 3);
});

const fullScoring = {
  s1_normativa: 5, s1_politica: 5, s1_analisis_riesgos: 4,
  s2_mfa: 4, s2_pam: 4,
  s3_bcp: 4, s3_rto_horas: 24, s3_rpo_horas: 4,
  s4_dpa: 5, s4_tia: 3, s4_paises_transferencia: 'India, México',
  s5_cloud_cert: 4,
  s6_subcontrata: 3,
};

test('compute_score: weighted total and thresholds', () => {
  const r = computeScore(fullScoring, []);
  // s1 4.67*.30 + s2 4*.25 + s3 4*.15 + s4 4*.20 + s5 4*.05 + s6 3*.05 = 4.15 -> 83
  assert.equal(r.score_total, 83);
  assert.equal(r.resultado, 'Aprobado');
  assert.equal(r.secciones.s3.controles, 1); // RTO/RPO hours are not scores
});

test('compute_score: blocking gap forces Rechazado', () => {
  const r = computeScore(fullScoring, [{ descripcion: 'Sin MFA', bloquea_aprobacion: true }]);
  assert.equal(r.resultado, 'Rechazado');
});

test('compute_score: section with >50% nulls -> Evaluación incompleta', () => {
  const r = computeScore({ ...fullScoring, s2_mfa: null, s2_pam: null, s2_access_review: null }, []);
  assert.equal(r.secciones.s2.media, null);
  assert.equal(r.score_total, null);
  assert.equal(r.resultado, 'Evaluación incompleta');
});

test('enrich builds DB params and falls back to the extracted vendor name', () => {
  const a = enrich(
    { vendor: { nombre: null, tier: 2 }, certificaciones: { iso_27001_hasta: '14/03/2027' }, scoring: fullScoring, gaps: [] },
    'TechNova Solutions S.L'
  );
  assert.equal(a.db.company_name, 'TechNova Solutions S.L');
  assert.equal(a.db.cert_expiry, '14/03/2027');
  assert.equal(a.db.overall_score, 83);
  assert.equal(a.db.current_risk, 'Aprobado');
  assert.equal(typeof a.db.scoring, 'string');
});
