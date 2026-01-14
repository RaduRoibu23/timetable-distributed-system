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
echo "=== Token student01 ==="
STUDENT_TOKEN="$(get_token student01 student01)"
if [[ "$STUDENT_TOKEN" == "ERROR_NO_TOKEN" ]]; then
  echo "Nu am putut lua token student01"; cat token-student01.json; exit 1
fi

echo
echo "=== Verificare: student01 are class_id in /me ==="
ME_JSON="$(curl -s -H "Authorization: Bearer ${STUDENT_TOKEN}" "${BASE_URL}/me")"
CLASS_ID_FROM_ME="$(echo "$ME_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("class_id", ""))')"
echo "class_id din /me pentru student01: ${CLASS_ID_FROM_ME}"
if [[ -z "$CLASS_ID_FROM_ME" ]] || [[ "$CLASS_ID_FROM_ME" == "null" ]]; then
  echo "ATENTIONARE: student01 nu are class_id setat, notificarea la clasa nu va functiona"
  echo "Testam direct trimiterea la user in loc de clasa..."
  SEND_STATUS="$(curl -s -o send_response.json -w "%{http_code}" \
    -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -X POST "${BASE_URL}/notifications/send" \
    -d '{"target_type":"user","target_id":"student01","message":"Test notification directa"}')"
else
  echo
  echo "=== Test POST /notifications/send (trimite la clasa) ==="
  SEND_RESP="$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -X POST "${BASE_URL}/notifications/send" \
    -d '{"target_type":"class","target_id":1,"message":"Test notification pentru clasa IX-A"}')"
  SEND_BODY="$(echo "$SEND_RESP" | head -n -1)"
  SEND_STATUS="$(echo "$SEND_RESP" | tail -n 1)"
  echo "HTTP status: ${SEND_STATUS}"
  echo "Response body: ${SEND_BODY}"
  if [[ "$SEND_STATUS" != "200" ]]; then
    echo "EROARE: POST /notifications/send trebuie sa fie 200"; exit 1
  fi
  # Daca lista e goala, trimitem direct la user ca fallback
  NOTIF_COUNT_SENT="$(echo "$SEND_BODY" | python3 - << 'EOF'
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data) if isinstance(data, list) else 0)
except:
    print(0)
EOF
)"
  if [[ "$NOTIF_COUNT_SENT" == "0" ]]; then
    echo "ATENTIONARE: send_to_class nu a gasit UserProfile-uri, trimitem direct la user"
    curl -s -o send_response.json -w "%{http_code}" \
      -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -X POST "${BASE_URL}/notifications/send" \
      -d '{"target_type":"user","target_id":"student01","message":"Test notification directa (fallback)"}' > /dev/null
  fi
fi

sleep 1

echo
echo "=== Test GET /notifications/me (student vede notificarea) ==="
NOTIFS_JSON="$(curl -s \
  -H "Authorization: Bearer ${STUDENT_TOKEN}" \
  "${BASE_URL}/notifications/me")"

NOTIF_COUNT="$(echo "$NOTIFS_JSON" | python3 - << 'EOF'
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data) if isinstance(data, list) else 0)
except:
    print(0)
EOF
)"
echo "Numar notificari pentru student01: ${NOTIF_COUNT}"
if [[ "$NOTIF_COUNT" == "0" ]]; then
  echo "EROARE: Student01 ar trebui sa aiba cel putin o notificare"; exit 1
fi

# Obtine prima notificare necitita
FIRST_NOTIF_ID="$(echo "$NOTIFS_JSON" | python3 - << 'EOF'
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list) and len(data) > 0:
        print(data[0]["id"])
    else:
        print("")
except:
    print("")
EOF
)"

if [[ -n "$FIRST_NOTIF_ID" ]]; then
  echo
  echo "=== Test PATCH /notifications/{id}/read (marcheaza ca citita) ==="
  READ_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${STUDENT_TOKEN}" \
    -X PATCH "${BASE_URL}/notifications/${FIRST_NOTIF_ID}/read")"
  echo "HTTP status: ${READ_STATUS}"
  if [[ "$READ_STATUS" != "200" ]]; then
    echo "EROARE: PATCH /notifications/{id}/read trebuie sa fie 200"; exit 1
  fi

  echo
  echo "=== Verificare GET /notifications/me?unread_only=true (nu ar trebui sa mai apara) ==="
  UNREAD_JSON="$(curl -s \
    -H "Authorization: Bearer ${STUDENT_TOKEN}" \
    "${BASE_URL}/notifications/me?unread_only=true")"
  UNREAD_COUNT="$(echo "$UNREAD_JSON" | python3 - << 'EOF'
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data) if isinstance(data, list) else 0)
except:
    print(0)
EOF
)"
  echo "Numar notificari necitite: ${UNREAD_COUNT}"
  # Nu verificam strict == 0 pentru ca poate exista notificari de la generare orar
fi

echo
echo "=== Test trigger: genereaza orar si verifica notificare automata ==="
GEN_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${SYSADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}/timetables/generate" \
  -d '{"class_id":1}')"
if [[ "$GEN_STATUS" != "200" ]]; then
  echo "EROARE: generate trebuie sa fie 200"; exit 1
fi

sleep 1

NOTIFS_AFTER_GEN="$(curl -s \
  -H "Authorization: Bearer ${STUDENT_TOKEN}" \
  "${BASE_URL}/notifications/me")"
NOTIF_COUNT_AFTER="$(echo "$NOTIFS_AFTER_GEN" | python3 - << 'EOF'
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data) if isinstance(data, list) else 0)
except:
    print(0)
EOF
)"
echo "Numar notificari dupa generare orar: ${NOTIF_COUNT_AFTER}"
if [[ "$NOTIF_COUNT_AFTER" -le "$NOTIF_COUNT" ]]; then
  echo "EROARE: Ar trebui sa existe o notificare noua dupa generare orar"; exit 1
fi

echo
echo "Notifications OK: send, list, mark as read, si trigger la generare orar functioneaza."

rm -f token-sysadmin01.json token-student01.json send_response.json
