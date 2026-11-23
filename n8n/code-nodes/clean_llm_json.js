// n8n Code node: "clean_llm_json"   (mode: Run Once for Each Item)
// Input : OpenRouter response -> choices[0].message.content
// Output: parsed TPRM assessment object
//
// LLMs often wrap JSON in ```json fences or add a sentence before/after.
// This strips that noise and fails loudly (with a preview) if it is not JSON.

function extractJson(raw) {
  if (raw && typeof raw === 'object') return raw;
  let text = String(raw || '').trim();
  text = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start === -1 || end === -1 || end < start) {
    throw new Error(`LLM response has no JSON object: ${text.slice(0, 200)}`);
  }
  const candidate = text.slice(start, end + 1);
  try {
    return JSON.parse(candidate);
  } catch (err) {
    throw new Error(`Invalid JSON from LLM (${err.message}): ${candidate.slice(0, 200)}`);
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { extractJson };
}

// ---- n8n entry point -------------------------------------------------------
if (typeof $input !== 'undefined') {
  const content = $input.item.json.choices?.[0]?.message?.content;
  return { json: extractJson(content) };
}
