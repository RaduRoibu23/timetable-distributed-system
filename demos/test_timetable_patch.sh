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
echo "=== Genereaza orar pentru IX-A (class_id=1) ==="
GEN_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/timetables/generate" \
  -d '{"class_id":1}')"
if [[ "$GEN_STATUS" != "200" ]]; then
  echo "EROARE: generate trebuie sa fie 200"; exit 1
fi

echo
echo "=== Obtine prima intrare din orar ==="
FIRST_ENTRY_JSON="$(curl -s \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  "${BASE_URL}/timetables/classes/1" | python3 -c 'import sys,json; print(json.dumps(json.load(sys.stdin)[0]))')"

ENTRY_ID="$(echo "$FIRST_ENTRY_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
ORIGINAL_SUBJECT_ID="$(echo "$FIRST_ENTRY_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["subject_id"])')"
echo "Entry ID: ${ENTRY_ID}, Original subject_id: ${ORIGINAL_SUBJECT_ID}"

echo
echo "=== Obtine o alta materie pentru test ==="
SUBJECTS_JSON="$(curl -s -H "Authorization: Bearer ${SYSADMIN_TOKEN}" "${BASE_URL}/subjects")"
NEW_SUBJECT_ID="$(echo "$SUBJECTS_JSON" | python3 -c 'import sys,json; subs=json.load(sys.stdin); print([s["id"] for s in subs if s["id"] != '${ORIGINAL_SUBJECT_ID}'][0])')"
echo "New subject_id pentru test: ${NEW_SUBJECT_ID}"

echo
echo "=== Test PATCH /timetables/entries/{id} (schimba subject_id) ==="
PATCH_STATUS="$(curl -s -o patch_response.json -w "%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X PATCH "${BASE_URL}/timetables/entries/${ENTRY_ID}" \
  -d "{\"subject_id\":${NEW_SUBJECT_ID}}")"
echo "HTTP status: ${PATCH_STATUS}"
if [[ "$PATCH_STATUS" != "200" ]]; then
  echo "EROARE: PATCH trebuie sa fie 200"; cat patch_response.json; exit 1
fi

UPDATED_SUBJECT_ID="$(cat patch_response.json | python3 -c 'import sys,json; print(json.load(sys.stdin)["subject_id"])')"
if [[ "$UPDATED_SUBJECT_ID" != "$NEW_SUBJECT_ID" ]]; then
  echo "EROARE: subject_id nu s-a actualizat corect (asteptat ${NEW_SUBJECT_ID}, primit ${UPDATED_SUBJECT_ID})"; exit 1
fi

echo "Subject_id actualizat corect: ${UPDATED_SUBJECT_ID}"

echo
echo "=== Test PATCH cu room_id (optional, daca exista rooms) ==="
# Obtine prima sala disponibila sau creeaza una
ROOMS_JSON="$(curl -s -H "Authorization: Bearer ${SYSADMIN_TOKEN}" "${BASE_URL}/rooms")"
ROOM_ID="$(echo "$ROOMS_JSON" | python3 - << 'EOF'
import sys, json
try:
    rooms = json.load(sys.stdin)
    if rooms and len(rooms) > 0:
        print(rooms[0]["id"])
    else:
        print("")
except:
    print("")
EOF
)"

if [[ -n "$ROOM_ID" ]]; then
  echo "Folosim sala cu ID: ${ROOM_ID}"
  PATCH_ROOM_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -X PATCH "${BASE_URL}/timetables/entries/${ENTRY_ID}" \
    -d "{\"room_id\":${ROOM_ID}}")"
  if [[ "$PATCH_ROOM_STATUS" != "200" ]]; then
    echo "EROARE: PATCH cu room_id trebuie sa fie 200"; exit 1
  fi
  echo "Room_id actualizat corect"
else
  echo "Nu exista rooms disponibile, sarim testul room_id"
fi

echo
echo "PATCH Timetable OK: putem edita manual intrari din orar (subject_id, room_id)."

rm -f token-sysadmin01.json patch_response.json
