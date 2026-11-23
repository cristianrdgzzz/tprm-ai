#!/usr/bin/env python3
# ruff: noqa: E501  (long strings are n8n expressions and sticky-note text)
"""
Generate n8n/workflows/TPRM_Pipeline.json from the versioned sources.

The Code nodes embed n8n/code-nodes/*.js and the Postgres nodes embed
n8n/sql/*.sql, so the importable workflow can never drift from the
unit-tested code. Run after editing any of them:

    python3 scripts/build_workflow.py
"""

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "n8n" / "code-nodes"
SQL = ROOT / "n8n" / "sql"
OUT = ROOT / "n8n" / "workflows" / "TPRM_Pipeline.json"

FILES = "/home/node/.n8n-files"
PG_CRED = {"postgres": {"id": "tprm-postgres", "name": "TPRM Postgres"}}


def nid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"tprm-ai/{name}"))


def sql(name: str) -> str:
    return "\n".join(
        line for line in (SQL / name).read_text(encoding="utf-8").splitlines()
        if not line.startswith("--")
    ).strip()


def node(name, ntype, version, pos, params, **extra):
    n = {
        "parameters": params,
        "id": nid(name),
        "name": name,
        "type": ntype,
        "typeVersion": version,
        "position": list(pos),
    }
    n.update(extra)
    return n


def code(name, file, pos):
    return node(name, "n8n-nodes-base.code", 2, pos, {
        "mode": "runOnceForEachItem",
        "jsCode": (CODE / file).read_text(encoding="utf-8"),
    })


def postgres(name, file, params_expr, pos, **extra):
    return node(name, "n8n-nodes-base.postgres", 2.5, pos, {
        "operation": "executeQuery",
        "query": sql(file),
        "options": {"queryReplacement": params_expr},
    }, credentials=PG_CRED, **extra)


def sticky(name, text, pos, w, h, color):
    return node(name, "n8n-nodes-base.stickyNote", 1, pos,
                {"content": text, "width": w, "height": h, "color": color})


Y0, YA, YB = 300, 120, 520   # main row, traceability branch, assessment branch

nodes = [
    sticky("Note · Ingest", "## 1 · Ingest\nPDFs from `n8n-files/input/`.\nScanned files (no text layer) go through **ocr-api** (Tesseract, spa+eng).",
           (-40, 60), 900, 420, 7),
    sticky("Note · Anonymize", "## 2 · Anonymize locally\n**presidio-es** returns `anonymized_text` + reversible `mapping`.\nNothing has left the machine yet.",
           (880, 60), 260, 420, 4),
    sticky("Note · Evidence", "## 3a · GDPR evidence\nMain vendor detection (ignores certifiers) → `vendors` → `anonymized_documents` (idempotent by content hash).",
           (1160, -80), 760, 320, 5),
    sticky("Note · Assess", "## 3b · LLM assessment\nOnly the **anonymized** text reaches OpenRouter. Placeholders are restored *after* the answer, in memory, and the score is computed in code.",
           (1160, 400), 1980, 320, 6),

    node("Manual Trigger", "n8n-nodes-base.manualTrigger", 1, (0, 200), {}),
    node("Every hour", "n8n-nodes-base.scheduleTrigger", 1.2, (0, 400),
         {"rule": {"interval": [{"field": "hours"}]}}),
    node("Read Files", "n8n-nodes-base.readWriteFile", 1, (220, Y0),
         {"operation": "read", "fileSelector": f"{FILES}/input/*.pdf", "options": {}}),
    node("Extract PDF", "n8n-nodes-base.extractFromFile", 1, (420, Y0),
         {"operation": "pdf", "options": {"keepSource": "binary"}}, alwaysOutputData=True),
    node("Has text layer?", "n8n-nodes-base.if", 2, (620, Y0), {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
            "conditions": [{
                "id": nid("cond-text"),
                "leftValue": "={{ ($json.text || '').trim().length }}",
                "rightValue": 50,
                "operator": {"type": "number", "operation": "gt"},
            }],
            "combinator": "and",
        },
        "options": {},
    }),
    node("OCR", "n8n-nodes-base.httpRequest", 4.2, (720, Y0 + 160), {
        "method": "POST",
        "url": "http://ocr_api:8000/ocr",
        "sendBody": True,
        "contentType": "multipart-form-data",
        "bodyParameters": {"parameters": [
            {"parameterType": "formBinaryData", "name": "file", "inputDataFieldName": "data"}
        ]},
        "options": {"timeout": 300000},
    }),
    node("PDF", "n8n-nodes-base.set", 3.4, (820, Y0), {
        "assignments": {"assignments": [
            {"id": nid("a-text"), "name": "text", "value": "={{ $json.text }}", "type": "string"},
            {"id": nid("a-file"), "name": "file_name",
             "value": "={{ $('Read Files').item.binary.data.fileName }}", "type": "string"},
        ]},
        "options": {},
    }),
    node("PRESIDIO", "n8n-nodes-base.httpRequest", 4.2, (1000, Y0), {
        "method": "POST",
        "url": "http://presidio_anonymizer:3000/anonymize",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ text: $json.text, language: 'es' }) }}",
        "options": {"timeout": 120000},
    }),

    # --- 3a traceability ---
    code("extract_vendor", "extract_vendor.js", (1220, YA)),
    postgres("upsert_vendor", "01_upsert_vendor_minimal.sql",
             "={{ [ $json.company_name ] }}", (1440, YA)),
    postgres("save_anonymized", "02_insert_anonymized_document.sql",
             "={{ [ String($json.id), $('PDF').item.json.file_name, "
             "$('extract_vendor').item.json.content_sha256, "
             "$('PRESIDIO').item.json.anonymized_text, "
             "JSON.stringify($('PRESIDIO').item.json.mapping) ] }}", (1660, YA)),

    # --- 3b assessment ---
    node("Lee Prompt", "n8n-nodes-base.readWriteFile", 1, (1220, YB),
         {"operation": "read", "fileSelector": f"{FILES}/maestro/prompt_tprm.txt", "options": {}}),
    node("Prompt as text", "n8n-nodes-base.extractFromFile", 1, (1420, YB),
         {"operation": "text", "options": {}}),
    code("build_prompt", "build_prompt.js", (1620, YB)),
    node("OpenRouter", "n8n-nodes-base.httpRequest", 4.2, (1820, YB), {
        "method": "POST",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "Authorization", "value": "=Bearer {{ $env.OPENROUTER_API_KEY }}"},
            {"name": "X-Title", "value": "TPRM-AI"},
        ]},
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify($json) }}",
        "options": {"timeout": 180000},
    }, retryOnFail=True, maxTries=3, waitBetweenTries=5000),
    code("clean_llm_json", "clean_llm_json.js", (2020, YB)),
    code("deanonymize", "deanonymize.js", (2220, YB)),
    code("compute_score", "compute_score.js", (2420, YB)),
    postgres("upsert_assessment", "03_upsert_vendor_assessment.sql",
             "={{ (() => { const d = $json.db; const s = v => v === null || v === undefined ? null : String(v);"
             " return [d.company_name, d.tipo_servicio, s(d.tier), d.dpo_nombre, d.dpo_email, d.dpo_tipo,"
             " d.country, d.localizacion_datos, d.subcontratistas, d.certificaciones, d.cert_expiry,"
             " d.scoring, d.gaps, d.campos_pendientes, s(d.overall_score), d.current_risk, d.summary]; })() }}",
             (2620, YB)),
    node("Move to processed", "n8n-nodes-base.executeCommand", 1, (2820, YB), {
        "command": "=mv \"" + FILES + "/input/{{ $('PDF').item.json.file_name }}\" \"" + FILES + "/processed/\"",
    }, onError="continueRegularOutput"),
    postgres("inventory", "04_export_inventory.sql", "", (3020, YB), executeOnce=True),
    node("CSV", "n8n-nodes-base.convertToFile", 1.1, (3220, YB),
         {"operation": "csv", "options": {"fileName": "inventario_vendors.csv"}}),
    node("Write inventory", "n8n-nodes-base.readWriteFile", 1, (3420, YB), {
        "operation": "write",
        "fileName": f"{FILES}/maestro/inventario_vendors.csv",
        "dataPropertyName": "data",
        "options": {},
    }),
]

# inventory has no query parameters
for n in nodes:
    if n["name"] == "inventory":
        n["parameters"]["options"] = {}


def link(*targets):
    return [[{"node": t, "type": "main", "index": 0} for t in targets]]


connections = {
    "Manual Trigger": {"main": link("Read Files")},
    "Every hour": {"main": link("Read Files")},
    "Read Files": {"main": link("Extract PDF")},
    "Extract PDF": {"main": link("Has text layer?")},
    "Has text layer?": {"main": [
        [{"node": "PDF", "type": "main", "index": 0}],
        [{"node": "OCR", "type": "main", "index": 0}],
    ]},
    "OCR": {"main": link("PDF")},
    "PDF": {"main": link("PRESIDIO")},
    "PRESIDIO": {"main": link("extract_vendor", "Lee Prompt")},
    "extract_vendor": {"main": link("upsert_vendor")},
    "upsert_vendor": {"main": link("save_anonymized")},
    "Lee Prompt": {"main": link("Prompt as text")},
    "Prompt as text": {"main": link("build_prompt")},
    "build_prompt": {"main": link("OpenRouter")},
    "OpenRouter": {"main": link("clean_llm_json")},
    "clean_llm_json": {"main": link("deanonymize")},
    "deanonymize": {"main": link("compute_score")},
    "compute_score": {"main": link("upsert_assessment")},
    "upsert_assessment": {"main": link("Move to processed")},
    "Move to processed": {"main": link("inventory")},
    "inventory": {"main": link("CSV")},
    "CSV": {"main": link("Write inventory")},
}

workflow = {
    "name": "TPRM - Pipeline",
    "nodes": nodes,
    "connections": connections,
    "active": False,
    "settings": {"executionOrder": "v1", "timezone": "Europe/Madrid"},
    "pinData": {},
    "meta": {"templateCredsSetupCompleted": False},
    "tags": [{"name": "tprm"}, {"name": "gdpr"}],
}

# sanity checks
names = {n["name"] for n in nodes}
for src, out in connections.items():
    assert src in names, src
    for branch in out["main"]:
        for c in branch:
            assert c["node"] in names, c["node"]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)} ({len(nodes)} nodes)")
