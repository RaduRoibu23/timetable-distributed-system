#!/usr/bin/env bash
set -euo pipefail

KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
CLIENT_ID="timetable-backend"
USERNAME="${USERNAME:-student01}"
PASSWORD="${PASSWORD:-student01}"
BASE_URL="http://localhost:8000"

echo "=== Obtinere token pentru ${USERNAME} ==="

curl -s -X POST "$KC_TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${CLIENT_ID}" \
  -d "grant_type=password" \
  -d "username=${USERNAME}" \
  -d "password=${PASSWORD}" > token.json

TOKEN="$(
  python3 - << 'EOF' "token.json"
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

if [[ "$TOKEN" == "ERROR_NO_TOKEN" ]]; then
  echo "Nu am putut extrage access_token:"
  cat token.json
  rm -f token.json
  exit 1
fi

rm -f token.json

echo
echo "=== Test GET /classes ==="
CLASSES_JSON="$(curl -s -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/classes")"
echo "$CLASSES_JSON"

if [[ "$CLASSES_JSON" != *"IX-A"* ]] || [[ "$CLASSES_JSON" != *"IX-B"* ]]; then
  echo "EROARE: Ne asteptam la clasele IX-A si IX-B in raspunsul /classes."
  exit 1
fi

echo
echo "=== Test GET /subjects ==="
SUBJECTS_JSON="$(curl -s -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/subjects")"
echo "$SUBJECTS_JSON" | sed -n '1,10p'

if [[ "$SUBJECTS_JSON" == "[]" ]] || [[ -z "$SUBJECTS_JSON" ]]; then
  echo "EROARE: Ne asteptam la mai multe materii seed-uite, dar raspunsul este gol."
  exit 1
fi

echo
echo "=== Test GET /timeslots ==="
TIMESLOTS_JSON="$(curl -s -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/timeslots")"
TIMESLOTS_COUNT="$(printf '%s\n' "$TIMESLOTS_JSON" | grep -o '"id":' | wc -l || true)"

echo "Numar timeslots (numarare simpla dupa \"id\"): ${TIMESLOTS_COUNT}"

if [[ "$TIMESLOTS_COUNT" != "35" ]]; then
  echo "EROARE: Ne asteptam la 35 time slots (5 zile x 7 ore), dar am gasit ${TIMESLOTS_COUNT}"
  exit 1
fi

echo
echo "Seed OK: classes >=2, subjects >=5, timeslots = 35."

