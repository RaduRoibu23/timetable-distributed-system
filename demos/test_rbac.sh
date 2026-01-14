#!/usr/bin/env bash
set -euo pipefail

# Small helper to obtain an access token for a given username/password
get_token() {
  local username="$1"
  local password="$2"

  local KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
  local CLIENT_ID="timetable-backend"

  curl -s -X POST "$KC_TOKEN_URL" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=${CLIENT_ID}" \
    -d "grant_type=password" \
    -d "username=${username}" \
    -d "password=${password}" > token-${username}.json

  local token
  token="$(
    python3 - << 'EOF' "token-${username}.json"
import json, sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
token = data.get("access_token")
if not token:
    print("ERROR_NO_TOKEN")
    sys.exit(0)
print(token)
EOF
  )"

  if [[ "$token" == "ERROR_NO_TOKEN" ]]; then
    echo "Nu am putut extrage access_token pentru utilizatorul '${username}':"
    cat "token-${username}.json"
    rm -f "token-${username}.json"
    exit 1
  fi

  echo "$token"
}

BASE_URL="http://localhost:8000"

echo "=== Obtinere token pentru student01 (rol student) ==="
STUDENT_TOKEN="$(get_token "student01" "student01")"

echo "=== Obtinere token pentru sysadmin01 (rol sysadmin) ==="
SYSADMIN_TOKEN="$(get_token "sysadmin01" "sysadmin01")"

echo
echo "=== Test 1: student01 incearca POST /rooms (AR TREBUI SA FIE 403) ==="
STUDENT_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${STUDENT_TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/rooms/" \
  -d '{"name":"RBAC_TEST_ROOM","capacity":10}')"

echo "HTTP status pentru student01: ${STUDENT_STATUS}"

if [[ "$STUDENT_STATUS" != "403" ]]; then
  echo "EROARE: Ne asteptam la 403 pentru student01 pe POST /rooms, dar am primit ${STUDENT_STATUS}"
  exit 1
fi

echo
echo "=== Test 2: sysadmin01 incearca POST /rooms (AR TREBUI SA FIE 200) ==="
SYSADMIN_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/rooms/" \
  -d '{"name":"RBAC_TEST_ROOM","capacity":10}')"

echo "HTTP status pentru sysadmin01: ${SYSADMIN_STATUS}"

if [[ "$SYSADMIN_STATUS" != "200" ]]; then
  echo "EROARE: Ne asteptam la 200 pentru sysadmin01 pe POST /rooms, dar am primit ${SYSADMIN_STATUS}"
  exit 1
fi

echo
echo "RBAC OK: student01 primit 403, sysadmin01 primit 200 pentru POST /rooms."

rm -f token-student01.json token-sysadmin01.json

