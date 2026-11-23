# Testing

| Level | What | How |
|---|---|---|
| Unit | n8n Code nodes (vendor detection, prompt building, JSON cleaning, de-anonymization, scoring) | `npm test` |
| Unit | Spanish recognizers + mapping anonymizer (Presidio fork) | `pytest` in `services/presidio-es/presidio` |
| Contract | Schema + every parameterised query is prepared against PostgreSQL 16 | CI job `database` |
| Sync | `TPRM_Pipeline.json` is regenerated from the sources and must not differ | CI job `code-nodes` |
| End-to-end | Full workflow executed by a real n8n against PostgreSQL, with stubbed Presidio and LLM | `tests/e2e/` (below) |

## End-to-end run (stubbed services)

`tests/e2e/stubs.py` serves a fake `presidio_anonymizer:3000/anonymize` and a fake `openrouter.ai` (self-signed TLS) that answers in the messy format real models use (text + ```json fences, wrong `score_total`). It logs every request, which lets you assert the privacy invariant.

```bash
echo "127.0.0.1 presidio_anonymizer openrouter.ai" | sudo tee -a /etc/hosts
openssl req -x509 -newkey rsa:2048 -nodes -keyout stub.key -out stub.crt -days 2 -subj "/CN=openrouter.ai"
sudo python3 tests/e2e/stubs.py &          # port 443 needs root
n8n import:workflow --input=n8n/workflows/TPRM_Pipeline.json
NODE_TLS_REJECT_UNAUTHORIZED=0 n8n execute --id <workflow-id>
grep chat/completions stub_requests.log | grep -c "TechNova"   # must be 0
```

Last run (n8n 1.x, PostgreSQL 16): all 21 executable nodes succeeded. The LLM request contained only placeholders, the vendor row was stored with `tier=2`, `overall_score=89` (the LLM claimed 99), `cert_expiry=2027-03-14`, the PDF was moved to `processed/` and `inventario_vendors.csv` was written.
