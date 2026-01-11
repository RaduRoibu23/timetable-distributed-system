#!/usr/bin/env bash
set -euo pipefail

# 0) CWD sigur (rezolvă getcwd errors)
cd "${HOME}"

# 1) Setări
WIN_REPO="${WIN_REPO:-/mnt/c/Users/roibu/Desktop/Facultateapl/ANUL 4/SCD/Proiect SCD/timetable-distributed-system}"
WSL_BASE="${WSL_BASE:-${HOME}/scd}"
WSL_REPO="${WSL_REPO:-${WSL_BASE}/timetable-distributed-system}"
SERVICE_DIR_REL="services/timetable-management-service"

echo "[1/5] Copy repo to WSL filesystem"
mkdir -p "${WSL_BASE}"

# Încercăm rsync, dacă pică facem fallback la cp
if command -v rsync >/dev/null 2>&1; then
  # IMPORTANT: rulează cu CWD sigur deja (HOME), deci nu mai crapă pe getcwd
  rsync -a --delete "${WIN_REPO}/" "${WSL_REPO}/" || true
fi

# Fallback dacă rsync nu a funcționat sau nu există
if [[ ! -d "${WSL_REPO}/.git" && ! -f "${WSL_REPO}/README.md" ]]; then
  echo "rsync failed or repo incomplete; using cp fallback..."
  rm -rf "${WSL_REPO}"
  mkdir -p "${WSL_REPO}"
  cp -a "${WIN_REPO}/." "${WSL_REPO}/"
fi

echo "[2/5] Recreate Python venv"
cd "${WSL_REPO}/${SERVICE_DIR_REL}"
rm -rf .venv
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[3/5] Quick import sanity check"
python - <<'PY'
import os
print("CWD:", os.getcwd())
import app
import app.main
print("Import OK: app.main")
PY

echo "[4/5] Export runtime env (adjust if you want)"
export KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8181}"
export OIDC_ISSUER="${OIDC_ISSUER:-http://localhost:8181/realms/timetable-realm}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://keycloak:keycloak@localhost:5432/keycloak}"

echo "[5/5] Start backend"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
