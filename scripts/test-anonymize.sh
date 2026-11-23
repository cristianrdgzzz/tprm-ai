#!/usr/bin/env bash
# Send a sample Spanish vendor text to presidio-es and print the result.
set -euo pipefail
URL="${PRESIDIO_URL:-http://localhost:5002}"
TEXT="${1:-Certificado emitido por SGS ICS Iberia a TechNova Solutions S.L. (CIF B12345678). DPO: Laura Martín Gómez, dpo@technova-solutions.eu, +34 912 345 678. Datos alojados en Irlanda.}"
python3 - "$URL" "$TEXT" <<'PY'
import json, sys, urllib.request
url, text = sys.argv[1], sys.argv[2]
req = urllib.request.Request(f"{url}/anonymize", data=json.dumps({"text": text}).encode(),
                             headers={"Content-Type": "application/json"})
print(json.dumps(json.load(urllib.request.urlopen(req)), ensure_ascii=False, indent=2))
PY
