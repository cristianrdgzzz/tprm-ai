#!/usr/bin/env bash
# Quick health check of every TPRM-AI service.
set -u
ok()   { printf "  \e[32m✔\e[0m %s\n" "$1"; }
fail() { printf "  \e[31m✘\e[0m %s\n" "$1"; }
check() { if curl -fsS -m 5 "$2" >/dev/null 2>&1; then ok "$1"; else fail "$1 ($2)"; fi; }

echo "TPRM-AI health check"
check "n8n            :5678" http://localhost:5678/healthz
check "presidio-es    :5002" http://localhost:5002/health
check "ocr-api        :8000" http://localhost:8000/health
check "qdrant         :6333" http://localhost:6333/collections
check "embedding-api  :8080 (profile rag)" http://localhost:8080/health
if docker exec tprm_postgres pg_isready -q 2>/dev/null; then ok "postgres       :5432"; else fail "postgres       :5432"; fi
