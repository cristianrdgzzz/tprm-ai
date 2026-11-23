-- Inventory export → Convert to File (CSV) → n8n-files/maestro/inventario_vendors.csv
-- Dates are formatted in SQL so the CSV is readable in Excel (es-ES).
SELECT id, company_name, tier, tipo_servicio, current_risk, overall_score,
       to_char(cert_expiry, 'DD/MM/YYYY')        AS cert_expiry,
       dpo_nombre, dpo_email, localizacion_datos,
       to_char(updated_at, 'DD/MM/YYYY HH24:MI') AS updated_at
FROM vendors
ORDER BY company_name;
