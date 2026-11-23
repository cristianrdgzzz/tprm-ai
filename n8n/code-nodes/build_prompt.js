// n8n Code node: "build_prompt"   (mode: Run Once for Each Item)
// Previous node: "Lee Prompt" (Read/Write Files from Disk -> Extract from File as text)
//   reading /home/node/.n8n-files/maestro/prompt_tprm.txt
// Output: OpenRouter chat-completions body -> { model, temperature, messages }
//
// The master prompt contains the marker [EL DOCUMENTO SE AÑADIRÁ AQUÍ].
// Everything except the document goes to the `system` role; the anonymized
// document goes alone to the `user` role. Only anonymized text ever leaves n8n.

const MARKER = '[EL DOCUMENTO SE AÑADIRÁ AQUÍ]';
const DEFAULT_MODEL = 'meta-llama/llama-3.3-70b-instruct:free';

function buildMessages(promptTemplate, anonymizedText) {
  if (!promptTemplate || !promptTemplate.includes(MARKER)) {
    throw new Error(`Prompt template is missing the marker ${MARKER}`);
  }
  const [before, after] = promptTemplate.split(MARKER);
  const system = `${before.replace(/DOCUMENTO A ANALIZAR:\s*$/i, '').trim()}\n\n${after.trim()}`;
  const user = `DOCUMENTO A ANALIZAR (anonimizado):\n\n${anonymizedText}`;
  return [
    { role: 'system', content: system },
    { role: 'user', content: user },
  ];
}

function buildBody(promptTemplate, anonymizedText, model) {
  return {
    model: model || DEFAULT_MODEL,
    temperature: 0,
    messages: buildMessages(promptTemplate, anonymizedText),
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { buildMessages, buildBody, MARKER };
}

// ---- n8n entry point -------------------------------------------------------
if (typeof $input !== 'undefined') {
  const prompt = $input.item.json.data;                       // text from "Lee Prompt"
  const anonymized = $('PRESIDIO').item.json.anonymized_text;
  const model = (typeof $env !== 'undefined' && $env.OPENROUTER_MODEL) || DEFAULT_MODEL;
  return { json: buildBody(prompt, anonymized, model) };
}
