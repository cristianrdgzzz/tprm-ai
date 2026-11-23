# Security policy

TPRM-AI processes third-party security documentation, so it is built to minimise data exposure.

## Reporting a vulnerability
Please open a private [security advisory](../../security/advisories/new) instead of a public issue.

## Security model
- **Data minimisation:** only anonymized text is sent to the external LLM. The reversible mapping stays in PostgreSQL.
- **Local by default:** every port is bound to `127.0.0.1`.
- **Secrets:** `.env` (git-ignored). Workflow exports never include n8n credentials; `scripts/export-workflows.sh` warns if an API key is hard-coded.
- **Containers:** custom services run as a non-root user.
- **No real data in git:** vendor documents, database and n8n data are git-ignored; only synthetic samples are versioned.

## Known limitations
- Anonymization is best-effort NLP: some Spanish person names can be missed. Review high-sensitivity documents before processing, or use a fully local LLM.
- PostgreSQL stores the mapping in clear text; protect the host disk (full-disk encryption) and the database credentials.
- This is a prototype, not a certified product. Do not use it as the sole basis for vendor approval decisions.
