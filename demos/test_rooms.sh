#!/bin/bash
set -e

BASE_URL="http://localhost:8000"
KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
CLIENT_ID="timetable-backend"
USERNAME="admin01"
PASSWORD="admin01"

echo "======================================"
echo "AUTHENTICATION"
echo "======================================"

TOKEN_RAW=$(curl -s -w "\n%{http_code}" -X POST "$KC_TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "grant_type=password" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD")

TOKEN_HTTP_CODE=$(printf "%s" "$TOKEN_RAW" | tail -n1)
TOKEN_BODY=$(printf "%s" "$TOKEN_RAW" | sed '$d')

if [ "$TOKEN_HTTP_CODE" != "200" ]; then
  echo "❌ EROARE: nu am putut obtine token (http $TOKEN_HTTP_CODE)"
  echo "$TOKEN_BODY"
  exit 1
fi

TOKEN=$(printf "%s" "$TOKEN_BODY" | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]\+\)".*/\1/p')

# fallback to python JSON parsing if sed didn't work
if [ -z "$TOKEN" ]; then
  TOKEN=$(printf "%s" "$TOKEN_BODY" | python3 - << 'PY'
import sys, json
s=sys.stdin.read()
try:
    data=json.loads(s)
    print(data.get('access_token',''))
except Exception:
    pass
PY
)
fi

if [ -z "$TOKEN" ]; then
  echo "❌ EROARE: token not found in response"
  echo "$TOKEN_BODY"
  exit 1
fi

echo "✔ Token obtinut"
echo ""

echo "======================================"
echo "CREATE / GET ROOM"
echo "======================================"

ROOM_NAME="A101"
ROOM_CAPACITY=30

ROOM_RAW=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/rooms/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"name\":\"$ROOM_NAME\",\"capacity\":$ROOM_CAPACITY}")

ROOM_HTTP_CODE=$(printf "%s" "$ROOM_RAW" | tail -n1)
ROOM_BODY=$(printf "%s" "$ROOM_RAW" | sed '$d')

ROOM_ID=""

# dacă POST a reușit, extragem id din răspuns
if [ "$ROOM_HTTP_CODE" = "200" ] || [ "$ROOM_HTTP_CODE" = "201" ]; then
  ROOM_ID=$(printf "%s" "$ROOM_BODY" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]\+\)".*/\1/p')
  if [ -z "$ROOM_ID" ]; then
    ROOM_ID=$(printf "%s" "$ROOM_BODY" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*\([0-9]\+\).*/\1/p')
  fi
  if [ -z "$ROOM_ID" ]; then
    ROOM_ID=$(printf "%s" "$ROOM_BODY" | python3 - << 'PY'
import sys, json
s=sys.stdin.read()
try:
    data=json.loads(s)
    print(data.get('id',''))
except Exception:
    pass
PY
)
  fi
fi

# dacă nu avem id după POST (ex: deja exista / conflict), îl căutăm în listă după nume
if [ -z "$ROOM_ID" ]; then
  ROOM_LIST_RAW=$(curl -s -w "\n%{http_code}" "$BASE_URL/rooms/" \
    -H "Authorization: Bearer $TOKEN")

  ROOM_LIST_HTTP_CODE=$(printf "%s" "$ROOM_LIST_RAW" | tail -n1)
  ROOM_LIST_BODY=$(printf "%s" "$ROOM_LIST_RAW" | sed '$d')

  if [ "$ROOM_LIST_HTTP_CODE" != "200" ]; then
    echo "❌ EROARE: nu pot lista rooms (http $ROOM_LIST_HTTP_CODE)"
    echo "$ROOM_LIST_BODY"
    echo "POST response (http $ROOM_HTTP_CODE):"
    echo "$ROOM_BODY"
    exit 1
  fi

  ROOM_ID=$(printf "%s" "$ROOM_LIST_BODY" | python3 - << 'PY'
import sys, json
s=sys.stdin.read()
target="A101"
try:
    rooms=json.loads(s)
    for r in rooms:
        if r.get('name')==target:
            print(r.get('id',''))
            break
except Exception:
    pass
PY
)
fi

if [ -z "$ROOM_ID" ]; then
  echo "❌ EROARE: nu pot obtine room id"
  echo "POST response (http $ROOM_HTTP_CODE):"
  echo "$ROOM_BODY"
  exit 1
fi

echo "Room folosit:"
echo "  id: $ROOM_ID"
echo ""

echo "======================================"
echo "LIST ROOMS"
echo "======================================"
curl -s "$BASE_URL/rooms/" -H "Authorization: Bearer $TOKEN"
echo ""
echo ""

echo "======================================"
echo "GET ROOM BY ID (initial)"
echo "======================================"

GET1_RAW=$(curl -s -w "\n%{http_code}" "$BASE_URL/rooms/$ROOM_ID" \
  -H "Authorization: Bearer $TOKEN")

GET1_HTTP_CODE=$(printf "%s" "$GET1_RAW" | tail -n1)
GET1_BODY=$(printf "%s" "$GET1_RAW" | sed '$d')

if [ "$GET1_HTTP_CODE" != "200" ]; then
  echo "❌ EROARE: nu pot face GET room (http $GET1_HTTP_CODE)"
  echo "$GET1_BODY"
  exit 1
fi

echo "$GET1_BODY"
echo ""

OLD_NAME=$(printf "%s" "$GET1_BODY" | python3 - << 'PY'
import sys, json
s=sys.stdin.read()
try:
    data=json.loads(s)
    print(data.get('name',''))
except Exception:
    pass
PY
)

echo "======================================"
echo "UPDATE ROOM (change name)"
echo "======================================"

NEW_NAME="${ROOM_NAME}-updated-$ROOM_ID"

UPD_RAW=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/rooms/$ROOM_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"name\":\"$NEW_NAME\",\"capacity\":$ROOM_CAPACITY}")

UPD_HTTP_CODE=$(printf "%s" "$UPD_RAW" | tail -n1)
UPD_BODY=$(printf "%s" "$UPD_RAW" | sed '$d')

if [ "$UPD_HTTP_CODE" != "200" ]; then
  echo "❌ EROARE: nu am putut face update room (http $UPD_HTTP_CODE)"
  echo "$UPD_BODY"
  exit 1
fi

echo "$UPD_BODY"
echo ""

echo "======================================"
echo "GET ROOM BY ID (after update) + VERIFY"
echo "======================================"

GET2_RAW=$(curl -s -w "\n%{http_code}" "$BASE_URL/rooms/$ROOM_ID" \
  -H "Authorization: Bearer $TOKEN")

GET2_HTTP_CODE=$(printf "%s" "$GET2_RAW" | tail -n1)
GET2_BODY=$(printf "%s" "$GET2_RAW" | sed '$d')

if [ "$GET2_HTTP_CODE" != "200" ]; then
  echo "❌ EROARE: nu pot face GET dupa update (http $GET2_HTTP_CODE)"
  echo "$GET2_BODY"
  exit 1
fi

echo "$GET2_BODY"
echo ""

VERIFY=$(python3 -c 'import sys, json
s=sys.stdin.read().strip()
d=json.loads(s) if s else {}
print(d.get("id",""))
print(d.get("name",""))' <<< "$GET2_BODY")

V_ID=$(printf "%s" "$VERIFY" | head -n1)
V_NAME=$(printf "%s" "$VERIFY" | sed -n '2p')


echo ""

echo "======================================"
echo "DELETE ROOM"
echo "======================================"

DEL_RAW=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/rooms/$ROOM_ID" \
  -H "Authorization: Bearer $TOKEN")

DEL_HTTP_CODE=$(printf "%s" "$DEL_RAW" | tail -n1)
DEL_BODY=$(printf "%s" "$DEL_RAW" | sed '$d')

if [ "$DEL_HTTP_CODE" != "200" ] && [ "$DEL_HTTP_CODE" != "204" ]; then
  echo "❌ EROARE: nu am putut sterge room (http $DEL_HTTP_CODE)"
  echo "$DEL_BODY"
  exit 1
fi

echo "✔ Room sters : ${ROOM_ID}"
[ -n "$DEL_BODY" ] && echo "$DEL_BODY"
echo ""

# aici vrem intenționat 404, deci dezactivăm temporar set -e
set +e

echo "======================================"
echo "DELETE AGAIN"
echo "======================================"

DEL2_RAW=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/rooms/$ROOM_ID" \
  -H "Authorization: Bearer $TOKEN")

DEL2_HTTP_CODE=$(printf "%s" "$DEL2_RAW" | tail -n1)
DEL2_BODY=$(printf "%s" "$DEL2_RAW" | sed '$d')

if [ "$DEL2_HTTP_CODE" != "404" ]; then
  echo "❌ EROARE: al doilea DELETE trebuia sa fie 404, dar este (http $DEL2_HTTP_CODE)"
  echo "$DEL2_BODY"
  exit 1
fi

echo "✔ OK: "
[ -n "$DEL2_BODY" ] && echo "$DEL2_BODY"
echo ""

exit 0
