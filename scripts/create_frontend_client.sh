#!/usr/bin/env bash
set -euo pipefail

# Script to create timetable-frontend client in Keycloak (run in WSL/bash)
# Usage: ./scripts/create_frontend_client.sh

KC_BASE="http://localhost:8181"
REALM="timetable-realm"
ADMIN_USER="admin"
ADMIN_PASS="admin"
CLIENT_ID="timetable-frontend"

echo "Requesting admin token from ${KC_BASE} ..."
TOKEN=$(curl -s -X POST "${KC_BASE}/realms/master/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=admin-cli&username=${ADMIN_USER}&password=${ADMIN_PASS}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: failed to get admin token. Check Keycloak is up and admin credentials." >&2
  exit 1
fi

echo "Checking if client '${CLIENT_ID}' exists in realm '${REALM}'..."
COUNT=$(curl -s -H "Authorization: Bearer $TOKEN" "${KC_BASE}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" | python3 -c 'import sys,json; arr=json.load(sys.stdin); print(len(arr))')
echo "Existing entries: $COUNT"
if [[ "$COUNT" -gt 0 ]]; then
  echo "Client '${CLIENT_ID}' already exists — nothing to do."
  exit 0
fi

echo "Creating client '${CLIENT_ID}'..."
cat > /tmp/newclient.json <<'JSON'
{
  "clientId": "timetable-frontend",
  "enabled": true,
  "protocol": "openid-connect",
  "publicClient": true,
  "directAccessGrantsEnabled": true,
  "standardFlowEnabled": true,
  "implicitFlowEnabled": false,
  "serviceAccountsEnabled": false,
  "rootUrl": "http://localhost:3000",
  "baseUrl": "http://localhost:3000",
  "redirectUris": ["http://localhost:3000/*"],
  "webOrigins": ["http://localhost:3000"],
  "attributes": { "post.logout.redirect.uris": "http://localhost:3000/*" }
}
JSON

HTTP=$(curl -s -o /tmp/resp -w "%{http_code}" -X POST "${KC_BASE}/admin/realms/${REALM}/clients" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data @/tmp/newclient.json)

echo "Create client HTTP status: $HTTP"
cat /tmp/resp || true

if [[ "$HTTP" =~ ^2 ]]; then
  echo "Client created successfully."
else
  echo "Client creation may have failed (HTTP $HTTP). Check /tmp/resp for details." >&2
  exit 1
fi

rm -f /tmp/newclient.json /tmp/resp
echo "Done."
