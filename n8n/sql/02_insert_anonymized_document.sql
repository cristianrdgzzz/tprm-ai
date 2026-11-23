-- Branch A (traceability): GDPR backup of what was sent to the LLM.
-- Query Parameters (in order):
--   $1 vendor_id        {{ $json.id }}
--   $2 file_name        {{ $('PDF').item.json.file_name }}
--   $3 content_sha256      {{ $('extract_vendor').item.json.content_sha256 }}
--   $4 anonymized_text  {{ $('PRESIDIO').item.json.anonymized_text }}
--   $5 entity_mapping   {{ JSON.stringify($('PRESIDIO').item.json.mapping) }}
-- Re-processing the same document is a no-op thanks to the UNIQUE content_sha256.
INSERT INTO anonymized_documents (vendor_id, file_name, content_sha256, anonymized_text, entity_mapping)
VALUES ($1, $2, $3, $4, $5::jsonb)
ON CONFLICT (content_sha256) DO NOTHING
RETURNING id;
