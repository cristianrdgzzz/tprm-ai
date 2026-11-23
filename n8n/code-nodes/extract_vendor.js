// n8n Code node: "extract_vendor"   (mode: Run Once for Each Item)
// Input : output of the PRESIDIO HTTP node -> { anonymized_text, mapping }
// Output: { company_name, company_placeholder, content_sha256 }
//
// Picks the *main* vendor among the COMPANY_* entities found by Presidio.
// Heuristic (fixes the old "COMPANY_001 is always the vendor" bug):
//   1. drop known certification bodies / auditors (SGS, AENOR, BSI, ...)
//   2. prefer names with a legal suffix (S.L., S.A., S.L.U., GmbH, Ltd, Inc...)
//   3. rank by number of mentions in the anonymized text, then by first position

const LEGAL_SUFFIX = /\b(S\.?\s?L\.?\s?U?\.?|S\.?\s?A\.?\s?U?\.?|S\.?\s?C\.?\s?A\.?|GmbH|Ltd\.?|Limited|Inc\.?|LLC|B\.?V\.?|SAS|SpA|AG)\s*$/i;

const CERTIFIERS = [
  'sgs', 'aenor', 'bureau veritas', 'bsi', 'tüv', 'tuv', 'dnv', 'lrqa', 'applus',
  'intertek', 'eqa', 'lloyd', 'kpmg', 'deloitte', 'pwc', 'ernst & young', 'ey ',
  'schellman', 'a-lign', 'coalfire', 'enac', 'ccn',
];

function isCertifier(name) {
  const n = ` ${name.toLowerCase()} `;
  return CERTIFIERS.some((c) => n.includes(` ${c.trim()}`));
}

function pickVendor(anonymizedText, mapping) {
  const text = anonymizedText || '';
  const candidates = Object.entries(mapping || {})
    .filter(([key]) => key.startsWith('COMPANY_'))
    .map(([key, value]) => {
      const tag = `<${key}>`;
      const mentions = text.split(tag).length - 1;
      const firstPos = text.indexOf(tag);
      return {
        key,
        value: String(value).trim(),
        mentions,
        firstPos: firstPos === -1 ? Number.MAX_SAFE_INTEGER : firstPos,
        legal: LEGAL_SUFFIX.test(String(value).trim()),
        certifier: isCertifier(String(value)),
      };
    })
    .filter((c) => !c.certifier);

  if (candidates.length === 0) return null;

  candidates.sort(
    (a, b) =>
      Number(b.legal) - Number(a.legal) ||
      b.mentions - a.mentions ||
      a.firstPos - b.firstPos
  );
  return candidates[0];
}

function sha256(text) {
  // NODE_FUNCTION_ALLOW_BUILTIN=crypto must be set for n8n (see docker-compose.yml)
  return require('crypto').createHash('sha256').update(text || '', 'utf8').digest('hex');
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { pickVendor, isCertifier, sha256 };
}

// ---- n8n entry point -------------------------------------------------------
if (typeof $input !== 'undefined') {
  const { anonymized_text, mapping } = $input.item.json;
  const vendor = pickVendor(anonymized_text, mapping);
  return {
    json: {
      company_name: vendor ? vendor.value : 'PROVEEDOR_NO_IDENTIFICADO',
      company_placeholder: vendor ? vendor.key : null,
      content_sha256: sha256(anonymized_text),
    },
  };
}
