// n8n Code node: "deanonymize"   (mode: Run Once for Each Item)
// Input : assessment JSON with placeholders (<COMPANY_001>, <EMAIL_001>, ...)
// Output: same JSON with the real values restored
//
// The mapping is taken from the PRESIDIO node of the *same execution*
// (in memory). It is never sent to the LLM.

const PLACEHOLDER = /<([A-Z_]+_\d{3})>/g;

function restore(value, mapping) {
  if (typeof value === 'string') {
    return value.replace(PLACEHOLDER, (match, key) =>
      Object.prototype.hasOwnProperty.call(mapping, key) ? mapping[key] : match
    );
  }
  if (Array.isArray(value)) return value.map((v) => restore(v, mapping));
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, restore(v, mapping)]));
  }
  return value;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { restore };
}

// ---- n8n entry point -------------------------------------------------------
if (typeof $input !== 'undefined') {
  const mapping = $('PRESIDIO').item.json.mapping || {};
  return { json: restore($input.item.json, mapping) };
}
