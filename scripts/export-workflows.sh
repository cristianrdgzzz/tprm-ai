#!/usr/bin/env bash
# Export every n8n workflow to n8n/workflows/ so it can be versioned in git.
# n8n stores workflows in PostgreSQL, so they are NOT in git unless you export them.
# Credentials are NOT exported (they stay encrypted inside n8n).
set -euo pipefail
cd "$(dirname "$0")/.."
docker exec tprm_n8n sh -c 'rm -rf /tmp/wf && mkdir -p /tmp/wf && n8n export:workflow --all --separate --pretty --output=/tmp/wf/'
docker cp tprm_n8n:/tmp/wf/. n8n/workflows/
# Strip execution-specific noise that changes on every export
for f in n8n/workflows/*.json; do
  python3 - "$f" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
for k in ("updatedAt", "createdAt", "versionId", "triggerCount", "shared", "staticData"):
    d.pop(k, None)
json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
PY
done
echo "Exported to n8n/workflows/:"; ls -1 n8n/workflows/*.json
grep -l -iE 'sk-or-v1-[a-z0-9]{10,}|Bearer [A-Za-z0-9_-]{20,}' n8n/workflows/*.json && \
  echo "WARNING: a workflow contains a hard-coded API key. Use \$env.OPENROUTER_API_KEY or n8n credentials." || true
