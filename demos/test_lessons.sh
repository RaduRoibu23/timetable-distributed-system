#!/bin/bash
set -e

BASE_URL="http://localhost:8000"
KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
CLIENT_ID="timetable-backend"
USERNAME="student1"
PASSWORD="student1"

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

ROOM_NAME="B202"

# incercam sa cream room-ul si capturam raspunsul
ROOM_RAW=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/rooms/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"name\":\"$ROOM_NAME\",\"capacity\":40}")

ROOM_HTTP_CODE=$(printf "%s" "$ROOM_RAW" | tail -n1)
ROOM_BODY=$(printf "%s" "$ROOM_RAW" | sed '$d')

# dacă crearea a avut succes, încercăm să extragem id-ul din corpul răspunsului
if [ "$ROOM_HTTP_CODE" = "200" ] || [ "$ROOM_HTTP_CODE" = "201" ]; then
  # try sed for quoted id
  ROOM_ID=$(printf "%s" "$ROOM_BODY" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]\+\)".*/\1/p')
  # fallback to numeric id
  if [ -z "$ROOM_ID" ]; then
    ROOM_ID=$(printf "%s" "$ROOM_BODY" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*\([0-9]\+\).*/\1/p')
  fi
  # final fallback to python JSON parsing
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

# dacă nu avem id după POST (ex: deja exista), căutăm în listă
if [ -z "$ROOM_ID" ]; then
  ROOM_LIST_RAW=$(curl -s -w "\n%{http_code}" "$BASE_URL/rooms/" \
    -H "Authorization: Bearer $TOKEN")

  ROOM_LIST_HTTP_CODE=$(printf "%s" "$ROOM_LIST_RAW" | tail -n1)
  ROOM_LIST_BODY=$(printf "%s" "$ROOM_LIST_RAW" | sed '$d')

  if [ "$ROOM_LIST_HTTP_CODE" != "200" ]; then
    echo "❌ EROARE: nu pot lista rooms (http $ROOM_LIST_HTTP_CODE)"
    echo "$ROOM_LIST_BODY"
    exit 1
  fi

  ROOM_ID=$(printf "%s" "$ROOM_LIST_BODY" | python3 - << 'PY'
import sys, json
s=sys.stdin.read()
try:
    rooms=json.loads(s)
    for r in rooms:
        if r.get('name')=="B202":
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
  echo "LIST response (http $ROOM_LIST_HTTP_CODE):"
  echo "$ROOM_LIST_BODY"
  exit 1
fi

echo "Room folosit:"
echo "  id: $ROOM_ID"
echo ""

echo "======================================"
echo "CREATE LESSON"
echo "======================================"

LESSON_RAW=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/lessons/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"title\": \"SCD\", \"weekday\": 2, \"start_time\": \"10:00:00\", \"end_time\": \"12:00:00\", \"room_id\": $ROOM_ID }")

LESSON_HTTP_CODE=$(printf "%s" "$LESSON_RAW" | tail -n1)
LESSON_BODY=$(printf "%s" "$LESSON_RAW" | sed '$d')

if [ "$LESSON_HTTP_CODE" != "200" ] && [ "$LESSON_HTTP_CODE" != "201" ]; then
  echo "❌ EROARE: lectia nu a fost creata (http $LESSON_HTTP_CODE)"
  echo "$LESSON_BODY"
  exit 1
fi

# try sed for quoted id
LESSON_ID=$(printf "%s" "$LESSON_BODY" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]\+\)".*/\1/p')
# fallback to numeric id
if [ -z "$LESSON_ID" ]; then
  LESSON_ID=$(printf "%s" "$LESSON_BODY" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*\([0-9]\+\).*/\1/p')
fi
# final fallback to python JSON parsing
if [ -z "$LESSON_ID" ]; then
  LESSON_ID=$(printf "%s" "$LESSON_BODY" | python3 - << 'PY'
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

if [ -z "$LESSON_ID" ]; then
  echo "❌ EROARE: lectia - id not found in response"
  echo "$LESSON_BODY"
  exit 1
fi

echo "Lectie initiala:"
curl -s "$BASE_URL/lessons/$LESSON_ID" \
  -H "Authorization: Bearer $TOKEN"
echo ""
echo ""

echo "======================================"
echo "UPDATE LESSON"
echo "======================================"

curl -s -X PUT "$BASE_URL/lessons/$LESSON_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"title\": \"SCD - updated\",
    \"weekday\": 3,
    \"start_time\": \"12:00:00\",
    \"end_time\": \"14:00:00\",
    \"room_id\": $ROOM_ID
  }" > /dev/null

echo "Lectie dupa update:"
curl -s "$BASE_URL/lessons/$LESSON_ID" \
  -H "Authorization: Bearer $TOKEN"
echo ""
echo ""

echo "======================================"
echo "LISTA LECTII (inainte de delete)"
echo "======================================"

curl -s "$BASE_URL/lessons/" \
  -H "Authorization: Bearer $TOKEN"
echo ""
echo ""

echo "======================================"
echo "DELETE LESSON"
echo "======================================"

DELETE_RAW=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/lessons/$LESSON_ID" \
  -H "Authorization: Bearer $TOKEN")

DELETE_HTTP_CODE=$(printf "%s" "$DELETE_RAW" | tail -n1)
DELETE_BODY=$(printf "%s" "$DELETE_RAW" | sed '$d')

if [ "$DELETE_HTTP_CODE" != "200" ] && [ "$DELETE_HTTP_CODE" != "204" ]; then
  echo "❌ EROARE: nu am putut sterge lectia (http $DELETE_HTTP_CODE)"
  echo "$DELETE_BODY"
  exit 1
fi

# If body contains deleted lesson, print its details
DEL_ID=$(printf "%s" "$DELETE_BODY" | python3 - << 'PY'
import sys, json
s=sys.stdin.read()
try:
    data=json.loads(s) if s.strip() else {}
    print(data.get('id',''))
    print(data.get('title',''))
    print(data.get('weekday',''))
    print(data.get('start_time',''))
    print(data.get('end_time',''))
    print(data.get('location',''))
except Exception:
    pass
PY
)

if [ -n "$DEL_ID" ]; then
  # python printed multiple lines; read them
  read -r D_ID D_TITLE D_WEEK D_START D_END D_LOC <<< "$DEL_ID"
  echo "✔ Lectie stearsa: id=$D_ID, title=$D_TITLE, weekday=$D_WEEK, start=$D_START, end=$D_END, location=$D_LOC"
else
  echo "✔ Lectie stearsa"
  [ -n "$DELETE_BODY" ] && echo "$DELETE_BODY"
fi
echo ""

echo "======================================"
echo "LISTA LECTII (dupa delete)"
echo "======================================"

curl -s "$BASE_URL/lessons/" \
  -H "Authorization: Bearer $TOKEN"
echo ""
