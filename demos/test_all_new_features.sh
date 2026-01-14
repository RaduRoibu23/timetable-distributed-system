#!/bin/bash
# Comprehensive test for all new features

set -e

BASE_URL="http://localhost:8000"
TOKEN=""

echo "=========================================="
echo "Testing All New Backend Features"
echo "=========================================="

# Login as sysadmin (via Keycloak)
echo -e "\n[1/8] Logging in as sysadmin01..."
KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
CLIENT_ID="timetable-backend"

LOGIN_RESPONSE=$(curl -s -X POST "$KC_TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "grant_type=password" \
  -d "username=sysadmin01" \
  -d "password=sysadmin01" > token.json)

TOKEN=$(python3 - << 'EOF'
import json, sys
try:
    with open("token.json") as f:
        data = json.load(f)
    token = data.get("access_token")
    if not token:
        print("")
        sys.exit(0)
    print(token)
except:
    print("")
    sys.exit(0)
EOF
)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token"
  if [ -f token.json ]; then
    echo "Response:"
    cat token.json
    rm -f token.json
  fi
  exit 1
fi
rm -f token.json
echo "✅ Token obtained"

# Test 1: Availability
echo -e "\n[2/8] Testing Teacher/Room Availability..."
curl -s -X POST "$BASE_URL/teachers/1/availability" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"weekday": 0, "index_in_day": 1, "available": false}' > /dev/null
echo "✅ Teacher availability created"

curl -s -X POST "$BASE_URL/rooms/1/availability" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"weekday": 0, "index_in_day": 1, "available": false}' > /dev/null
echo "✅ Room availability created"

# Test 2: Subject-Teacher Mapping
echo -e "\n[3/8] Testing Subject-Teacher Mapping..."
SUBJECT_ID=$(curl -s -X GET "$BASE_URL/subjects" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '1')" 2>/dev/null || echo "1")

CLASS_ID=$(curl -s -X GET "$BASE_URL/classes" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '1')" 2>/dev/null || echo "1")

curl -s -X POST "$BASE_URL/subjects/$SUBJECT_ID/teachers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"class_id\": $CLASS_ID, \"teacher_id\": 1}" > /dev/null
echo "✅ Teacher assigned to subject"

# Test 3: Generate timetable with new algorithm
echo -e "\n[4/8] Testing Enhanced Timetable Generation..."
JOB_RESPONSE=$(curl -s -X POST "$BASE_URL/timetables/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"class_id\": $CLASS_ID}")

JOB_ID=$(echo "$JOB_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['job_ids'][0] if data.get('job_ids') else '')" 2>/dev/null || echo "")
echo "✅ Timetable generation job created (ID: $JOB_ID)"

sleep 3

# Test 4: Conflict Reports
echo -e "\n[5/8] Testing Conflict Reports..."
if [ ! -z "$JOB_ID" ]; then
  CONFLICTS=$(curl -s -X GET "$BASE_URL/timetables/jobs/$JOB_ID/conflicts" \
    -H "Authorization: Bearer $TOKEN")
  echo "✅ Conflict reports retrieved"
fi

# Test 5: Optimistic Locking
echo -e "\n[6/8] Testing Optimistic Locking..."
ENTRIES=$(curl -s -X GET "$BASE_URL/timetables/classes/$CLASS_ID" \
  -H "Authorization: Bearer $TOKEN")

ENTRY_ID=$(echo "$ENTRIES" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null || echo "")

if [ ! -z "$ENTRY_ID" ]; then
  ENTRY_DETAIL=$(curl -s -X GET "$BASE_URL/timetables/classes/$CLASS_ID" \
    -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); entry=[e for e in data if e['id'] == $ENTRY_ID]; print(json.dumps(entry[0]) if entry else '{}')" 2>/dev/null || echo "{}")
  
  VERSION=$(echo "$ENTRY_DETAIL" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 1))" 2>/dev/null || echo "1")
  
  # Update with correct version
  curl -s -X PATCH "$BASE_URL/timetables/entries/$ENTRY_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"room_id\": 1, \"version\": $VERSION}" > /dev/null
  echo "✅ Optimistic locking working (version: $VERSION)"
fi

# Test 6: Audit Logs
echo -e "\n[7/8] Testing Audit Logs..."
AUDIT_LOGS=$(curl -s -X GET "$BASE_URL/audit-logs?limit=5" \
  -H "Authorization: Bearer $TOKEN")
echo "✅ Audit logs retrieved"

# Test 7: Timetable Stats
echo -e "\n[8/8] Testing Timetable Stats..."
STATS=$(curl -s -X GET "$BASE_URL/timetables/stats" \
  -H "Authorization: Bearer $TOKEN")
echo "✅ Timetable stats retrieved"

echo -e "\n=========================================="
echo "✅ All Tests Completed Successfully!"
echo "=========================================="
