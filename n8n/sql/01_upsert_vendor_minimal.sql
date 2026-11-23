-- Branch A (traceability): make sure the vendor exists and get its id.
-- n8n Postgres node → Execute Query → Query Parameters: {{ $json.company_name }}
INSERT INTO vendors (company_name)
VALUES ($1)
ON CONFLICT (company_name) DO UPDATE SET company_name = EXCLUDED.company_name
RETURNING id;
