#!/usr/bin/env bash
set -euo pipefail

KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
CLIENT_ID="timetable-backend"
BASE_URL="http://localhost:8000"

get_token() {
  local username="$1"
  local password="$2"
  curl -s -X POST "$KC_TOKEN_URL" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=${CLIENT_ID}" \
    -d "grant_type=password" \
    -d "username=${username}" \
    -d "password=${password}" > "token-${username}.json"

  python3 - << 'EOF' "token-${username}.json"
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
tok = data.get("access_token")
if not tok:
    print("ERROR_NO_TOKEN")
else:
    print(tok)
EOF
}

echo "=== Token scheduler01 ==="
SCHEDULER_TOKEN="$(get_token scheduler01 scheduler01)"
if [[ "$SCHEDULER_TOKEN" == "ERROR_NO_TOKEN" ]]; then
  echo "Nu am putut lua token scheduler01"; cat token-scheduler01.json; exit 1
fi

echo
echo "=== Test POST /schedule/run (alias pentru /timetables/generate) ==="
SCHEDULE_STATUS="$(curl -s -o schedule_response.json -w "%{http_code}" \
  -H "Authorization: Bearer ${SCHEDULER_TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/schedule/run" \
  -d '{"class_id":1}')"
echo "HTTP status: ${SCHEDULE_STATUS}"
if [[ "$SCHEDULE_STATUS" != "200" ]]; then
  echo "EROARE: POST /schedule/run trebuie sa fie 200"; cat schedule_response.json; exit 1
fi

ENTRIES_COUNT="$(cat schedule_response.json | python3 - << 'EOF'
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data) if isinstance(data, list) else 0)
except:
    print(0)
EOF
)"
echo "Entries returned: ${ENTRIES_COUNT}"
if [[ "$ENTRIES_COUNT" != "35" ]]; then
  echo "EROARE: Ne asteptam la 35 entries pentru clasa 1"; exit 1
fi

echo
echo "=== Token professor01 ==="
PROFESSOR_TOKEN="$(get_token professor01 professor01)"
if [[ "$PROFESSOR_TOKEN" == "ERROR_NO_TOKEN" ]]; then
  echo "Nu am putut lua token professor01"; cat token-professor01.json; exit 1
fi

echo
echo "=== Test GET /lessons/mine (alias pentru /timetables/me) ==="
LESSONS_MINE_STATUS="$(curl -s -o lessons_mine.json -w "%{http_code}" \
  -H "Authorization: Bearer ${PROFESSOR_TOKEN}" \
  "${BASE_URL}/lessons/mine?class_id=1")"
echo "HTTP status: ${LESSONS_MINE_STATUS}"
if [[ "$LESSONS_MINE_STATUS" != "200" ]]; then
  echo "EROARE: GET /lessons/mine trebuie sa fie 200"; cat lessons_mine.json; exit 1
fi

echo
echo "=== Token admin01 ==="
ADMIN_TOKEN="$(get_token admin01 admin01)"
if [[ "$ADMIN_TOKEN" == "ERROR_NO_TOKEN" ]]; then
  echo "Nu am putut lua token admin01"; cat token-admin01.json; exit 1
fi

echo
echo "=== Test GET /users (compat pentru admin) ==="
USERS_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  "${BASE_URL}/users")"
echo "HTTP status: ${USERS_STATUS}"
if [[ "$USERS_STATUS" != "200" ]]; then
  echo "EROARE: GET /users trebuie sa fie 200"; exit 1
fi

echo
echo "Frontend compat OK: /schedule/run, /lessons/mine, /users functioneaza."

rm -f token-scheduler01.json token-professor01.json token-admin01.json schedule_response.json lessons_mine.json
