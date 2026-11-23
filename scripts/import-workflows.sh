#!/usr/bin/env bash
# Import the versioned workflows from n8n/workflows/ into a fresh n8n instance.
set -euo pipefail
cd "$(dirname "$0")/.."
docker cp n8n/workflows/. tprm_n8n:/tmp/wf/
docker exec tprm_n8n n8n import:workflow --separate --input=/tmp/wf/
