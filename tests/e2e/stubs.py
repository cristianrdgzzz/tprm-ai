"""
Stub services for the end-to-end run of the n8n workflow (see docs/TESTING.md).

- http://presidio_anonymizer:3000/anonymize  -> fixed mapping for a synthetic vendor
- https://openrouter.ai/api/v1/chat/completions -> a messy but realistic LLM answer
  (prose + ```json fences, wrong score_total) to exercise clean_llm_json / compute_score

Every request body is appended to stub_requests.log so the privacy invariant can be
checked: the LLM request must contain placeholders only, never real values.
"""

import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

MAPPING = {
    "COMPANY_001": "SGS ICS Iberia",
    "COMPANY_002": "TechNova Solutions S.L",
    "EMAIL_001": "dpo@technova-solutions.eu",
    "LOCATION_001": "Irlanda",
}

LLM_ANSWER = {
    "vendor": {
        "nombre": "<COMPANY_002>",
        "tipo_servicio": "SaaS",
        "tier": 2,
        "dpo_email": "<EMAIL_001>",
        "localizacion_datos": "<LOCATION_001>",
        "subcontratistas": [],
    },
    "certificaciones": {"iso_27001_hasta": "14/03/2027"},
    "scoring": {
        "s1_normativa": 5, "s1_politica": 4,
        "s2_mfa": 5, "s2_pam": 4, "s2_access_review": 4,
        "s3_bcp": 4, "s4_dpa": 5, "s5_cloud_cert": 4, "s6_subcontrata": 4,
        "score_total": 99,          # deliberately wrong: the pipeline must recompute it
        "resultado": "Aprobado",
    },
    "gaps": [],
    "campos_pendientes": ["s4_tia"],
    "resumen_ejecutivo": "<COMPANY_002> certificado por <COMPANY_001>.",
}

LOG = open("stub_requests.log", "a", encoding="utf-8")


def anonymize(text: str) -> dict:
    for key, value in sorted(MAPPING.items(), key=lambda kv: -len(kv[1])):
        text = text.replace(value, f"<{key}>")
    return {"anonymized_text": text, "mapping": MAPPING}


def llm_response() -> dict:
    content = "Aquí tienes:\n```json\n" + json.dumps(LLM_ANSWER, ensure_ascii=False) + "\n```"
    return {"choices": [{"message": {"content": content}}]}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        LOG.write(f"{self.path} {json.dumps(body, ensure_ascii=False)}\n")
        LOG.flush()
        out = anonymize(body["text"]) if self.path == "/anonymize" else llm_response()
        payload = json.dumps(out, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    presidio = HTTPServer(("0.0.0.0", 3000), Handler)
    threading.Thread(target=presidio.serve_forever, daemon=True).start()

    llm = HTTPServer(("0.0.0.0", 443), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain("stub.crt", "stub.key")
    llm.socket = ctx.wrap_socket(llm.socket, server_side=True)
    llm.serve_forever()
