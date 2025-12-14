#!/usr/bin/env bash
set -euo pipefail

# ================== Config Keycloak + backend ==================
KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
CLIENT_ID="timetable-backend"
BACKEND_URL="http://localhost:8000"

# User implicit (poți override cu: USERNAME=... PASSWORD=... ./test_lessons.sh)
USERNAME="${USERNAME:-student1}"
PASSWORD="${PASSWORD:-student1}"

# ================== 1. Obține access_token ==================

RESPONSE=$(
  curl -s -X POST "$KC_TOKEN_URL" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$CLIENT_ID" \
    -d "grant_type=password" \
    -d "username=$USERNAME" \
    -d "password=$PASSWORD"
)

ACCESS_TOKEN=$(
  KC_RESPONSE="$RESPONSE" \
  python3 - << 'PY'
import json, os
data_raw = os.environ.get("KC_RESPONSE", "")
try:
    data = json.loads(data_raw)
    token = data.get("access_token") or ""
    print(token)
except Exception:
    print("")
PY
)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "Token FAIL"
  echo "$RESPONSE"
  exit 1
fi

# ================== 2. POST /lessons ==================

TMP_POST=$(mktemp)

HTTP_CODE_POST=$(
  curl -s -o "$TMP_POST" -w "%{http_code}" \
    -X POST "$BACKEND_URL/lessons/" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "title": "Test Lesson from script",
      "weekday": 2,
      "start_time": "09:00:00",
      "end_time": "10:00:00",
      "location": "Script Room"
    }'
)

if [ "$HTTP_CODE_POST" != "200" ] && [ "$HTTP_CODE_POST" != "201" ]; then
  echo "Post FAIL ($HTTP_CODE_POST)"
  cat "$TMP_POST"
  exit 1
fi

# extragem id + info pentru mesaj
LESSON_ID=$(
  LESSON_POST_FILE="$TMP_POST" \
  python3 - << 'PY'
import json, os
path = os.environ.get("LESSON_POST_FILE", "")
if not path:
    print("")
    raise SystemExit(0)

with open(path) as f:
    data = json.load(f)

print(data.get("id", ""))
PY
)

if [ -z "$LESSON_ID" ]; then
  echo "Post FAIL (no id in response)"
  cat "$TMP_POST"
  exit 1
fi

LESSON_INFO=$(
  LESSON_POST_FILE="$TMP_POST" \
  python3 - << 'PY'
import json, os
path = os.environ.get("LESSON_POST_FILE", "")
with open(path) as f:
    data = json.load(f)

id_ = data.get("id")
title = data.get("title")
weekday = data.get("weekday")
start_time = data.get("start_time")
end_time = data.get("end_time")
location = data.get("location")

print(f'id={id_} title="{title}" weekday={weekday} {start_time}-{end_time} location="{location}"')
PY
)

echo "Post OK: created lesson ${LESSON_INFO}"

# ================== 3. GET /lessons ==================

TMP_GET=$(mktemp)

HTTP_CODE_GET=$(
  curl -s -o "$TMP_GET" -w "%{http_code}" \
    -X GET "$BACKEND_URL/lessons/" \
    -H "Authorization: Bearer $ACCESS_TOKEN"
)

if [ "$HTTP_CODE_GET" != "200" ]; then
  echo "Get FAIL ($HTTP_CODE_GET)"
  cat "$TMP_GET"
  exit 1
fi

# numărăm câte lecții sunt în listă
LESSON_COUNT=$(
  TMP_GET="$TMP_GET" \
  python3 - << 'PY'
import os, json, sys
path = os.environ.get("TMP_GET", "")
try:
    with open(path) as f:
        data = json.load(f)
except Exception:
    print("")
    sys.exit(1)

if not isinstance(data, list):
    print("")
    sys.exit(1)

print(len(data))
PY
)

if [ -z "$LESSON_COUNT" ]; then
  echo "Get FAIL (response not a list / cannot count lessons)"
  cat "$TMP_GET"
  exit 1
fi

# verificăm că id-ul creat este în listă
LESSON_ID="$LESSON_ID" TMP_GET="$TMP_GET" \
python3 - << 'PY'
import os, json, sys

lesson_id_raw = os.environ.get("LESSON_ID", "")
tmp_get = os.environ.get("TMP_GET", "")

try:
    lesson_id = int(lesson_id_raw)
except Exception:
    print("Get FAIL (invalid LESSON_ID)")
    sys.exit(1)

try:
    with open(tmp_get) as f:
        data = json.load(f)
except Exception as e:
    print("Get FAIL (cannot read GET response file)", e)
    sys.exit(1)

if not isinstance(data, list):
    print("Get FAIL (response not a list)")
    sys.exit(1)

if any(item.get("id") == lesson_id for item in data):
    sys.exit(0)

print("Get FAIL (id not found in list)")
sys.exit(1)
PY

echo "Get OK: lesson id=${LESSON_ID} is present in list (total ${LESSON_COUNT} lessons)"
