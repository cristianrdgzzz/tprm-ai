#!/usr/bin/env bash
# Create the RAG collections in Qdrant (idempotent). Vectors: multilingual-e5-large (1024d).
set -euo pipefail
QDRANT="${QDRANT_URL:-http://localhost:6333}"
for c in vendors_docs vendors_assessments; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$QDRANT/collections/$c")
  if [ "$code" = "200" ]; then echo "= $c already exists"; continue; fi
  curl -fsS -X PUT "$QDRANT/collections/$c" -H 'Content-Type: application/json' \
       -d '{"vectors": {"size": 1024, "distance": "Cosine"}}' >/dev/null
  echo "+ created $c"
done
