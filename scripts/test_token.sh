#!/usr/bin/env bash
set -euo pipefail

KC_BASE="http://localhost:8181"
REALM="timetable-realm"
CLIENT_ID="timetable-frontend"
USERNAME="student01"
PASSWORD="student01"

echo "Requesting token for ${USERNAME}..."
HTTP=$(curl -s -o /tmp/resp -w '%{http_code}' -X POST "${KC_BASE}/realms/${REALM}/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=${CLIENT_ID}&username=${USERNAME}&password=${PASSWORD}")

echo "HTTP:$HTTP"
echo "RESPONSE:" 
cat /tmp/resp || true
