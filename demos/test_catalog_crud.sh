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

echo
echo "=== Test POST /classes (creare clasa noua) ==="
CREATE_CLASS_RESP="$(curl -s -w "\n%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/classes" \
  -d '{"name":"X-A"}')"
CREATE_CLASS_BODY="$(echo "$CREATE_CLASS_RESP" | head -n -1)"
CREATE_CLASS_STATUS="$(echo "$CREATE_CLASS_RESP" | tail -n 1)"
echo "HTTP status: ${CREATE_CLASS_STATUS}"
if [[ "$CREATE_CLASS_STATUS" != "200" ]]; then
  echo "EROARE: POST /classes trebuie sa fie 200"; echo "$CREATE_CLASS_BODY"; exit 1
fi

CLASS_ID="$(echo "$CREATE_CLASS_BODY" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
echo "Clasa creata cu ID: ${CLASS_ID}"

echo
echo "=== Test PUT /classes/{id} (update clasa) ==="
UPDATE_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X PUT "${BASE_URL}/classes/${CLASS_ID}" \
  -d '{"name":"X-B"}')"
echo "HTTP status: ${UPDATE_STATUS}"
if [[ "$UPDATE_STATUS" != "200" ]]; then
  echo "EROARE: PUT /classes/{id} trebuie sa fie 200"; exit 1
fi

echo
echo "=== Test DELETE /classes/{id} ==="
DELETE_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -X DELETE "${BASE_URL}/classes/${CLASS_ID}")"
echo "HTTP status: ${DELETE_STATUS}"
if [[ "$DELETE_STATUS" != "200" ]]; then
  echo "EROARE: DELETE /classes/{id} trebuie sa fie 200"; exit 1
fi

echo
echo "=== Test POST /subjects (creare materie noua) ==="
CREATE_SUBJECT_RESP="$(curl -s -w "\n%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/subjects" \
  -d '{"name":"Test Subject","short_code":"TEST"}')"
CREATE_SUBJECT_BODY="$(echo "$CREATE_SUBJECT_RESP" | head -n -1)"
CREATE_SUBJECT_STATUS="$(echo "$CREATE_SUBJECT_RESP" | tail -n 1)"
echo "HTTP status: ${CREATE_SUBJECT_STATUS}"
if [[ "$CREATE_SUBJECT_STATUS" != "200" ]]; then
  echo "EROARE: POST /subjects trebuie sa fie 200"; echo "$CREATE_SUBJECT_BODY"; exit 1
fi

SUBJECT_ID="$(echo "$CREATE_SUBJECT_BODY" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
echo "Materie creata cu ID: ${SUBJECT_ID}"

echo
echo "=== Test PUT /subjects/{id} ==="
UPDATE_SUBJECT_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X PUT "${BASE_URL}/subjects/${SUBJECT_ID}" \
  -d '{"name":"Test Subject Updated","short_code":"TEST2"}')"
echo "HTTP status: ${UPDATE_SUBJECT_STATUS}"
if [[ "$UPDATE_SUBJECT_STATUS" != "200" ]]; then
  echo "EROARE: PUT /subjects/{id} trebuie sa fie 200"; exit 1
fi

echo
echo "=== Test POST /curricula (creare curriculum) ==="
# Folosim class_id=1 (IX-A) si subject_id nou creat
CREATE_CURR_RESP="$(curl -s -w "\n%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/curricula" \
  -d "{\"class_id\":1,\"subject_id\":${SUBJECT_ID},\"hours_per_week\":2}")"
CREATE_CURR_BODY="$(echo "$CREATE_CURR_RESP" | head -n -1)"
CREATE_CURR_STATUS="$(echo "$CREATE_CURR_RESP" | tail -n 1)"
echo "HTTP status: ${CREATE_CURR_STATUS}"
if [[ "$CREATE_CURR_STATUS" != "200" ]]; then
  echo "EROARE: POST /curricula trebuie sa fie 200"; echo "$CREATE_CURR_BODY"; exit 1
fi

CURR_ID="$(echo "$CREATE_CURR_BODY" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
echo "Curriculum creat cu ID: ${CURR_ID}"

echo
echo "=== Test PUT /curricula/{id} ==="
UPDATE_CURR_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X PUT "${BASE_URL}/curricula/${CURR_ID}" \
  -d '{"hours_per_week":3}')"
echo "HTTP status: ${UPDATE_CURR_STATUS}"
if [[ "$UPDATE_CURR_STATUS" != "200" ]]; then
  echo "EROARE: PUT /curricula/{id} trebuie sa fie 200"; exit 1
fi

echo
echo "=== Cleanup: DELETE test resources ==="
curl -s -o /dev/null -H "Authorization: Bearer ${SYSADMIN_TOKEN}" -X DELETE "${BASE_URL}/curricula/${CURR_ID}"
curl -s -o /dev/null -H "Authorization: Bearer ${SYSADMIN_TOKEN}" -X DELETE "${BASE_URL}/subjects/${SUBJECT_ID}"

echo
echo "CRUD Catalog OK: toate operatiile (POST/PUT/DELETE) functioneaza pentru classes, subjects, curricula."

rm -f token-sysadmin01.json
