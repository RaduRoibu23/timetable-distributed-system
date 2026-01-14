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

echo "=== Token sysadmin01 ==="
SYSADMIN_TOKEN="$(get_token sysadmin01 sysadmin01)"
if [[ "$SYSADMIN_TOKEN" == "ERROR_NO_TOKEN" ]]; then
  echo "Nu am putut lua token sysadmin01"; cat token-sysadmin01.json; exit 1
fi

echo "=== Genereaza orar pentru IX-A (class_id=1) ==="
GEN_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/timetables/generate" \
  -d '{"class_id":1}')"
echo "HTTP status generate: ${GEN_STATUS}"
if [[ "$GEN_STATUS" != "200" ]]; then
  echo "EROARE: generate trebuie sa fie 200"; exit 1
fi

echo "=== Token student01 ==="
STUDENT_TOKEN="$(get_token student01 student01)"
if [[ "$STUDENT_TOKEN" == "ERROR_NO_TOKEN" ]]; then
  echo "Nu am putut lua token student01"; cat token-student01.json; exit 1
fi

echo "=== Student01 vede /timetables/me (fara param) ==="
ME_STATUS="$(curl -s -o me.json -w "%{http_code}" \
  -H "Authorization: Bearer ${STUDENT_TOKEN}" \
  "${BASE_URL}/timetables/me")"
echo "HTTP status /timetables/me: ${ME_STATUS}"
if [[ "$ME_STATUS" != "200" ]]; then
  echo "EROARE: /timetables/me trebuie sa fie 200 pentru student"; cat me.json; exit 1
fi

COUNT="$(python3 - << 'EOF'
import json
with open("me.json") as f:
    data = json.load(f)
print(len(data))
EOF
)"
echo "Entries returned: ${COUNT}"
if [[ "$COUNT" != "35" ]]; then
  echo "EROARE: Ne asteptam la 35 entries pentru student (5x7)."; exit 1
fi

echo "OK: student vede doar orarul clasei lui (35 intrari)."

rm -f token-sysadmin01.json token-student01.json me.json

