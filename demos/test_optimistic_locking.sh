#!/bin/bash
# Test optimistic locking

set -e

BASE_URL="http://localhost:8000"
TOKEN=""

echo "=== Testing Optimistic Locking ==="

# Login as sysadmin (via Keycloak)
echo "Logging in as sysadmin01..."
KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
CLIENT_ID="timetable-backend"

curl -s -X POST "$KC_TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "grant_type=password" \
  -d "username=sysadmin01" \
  -d "password=sysadmin01" > token.json

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
  echo "Failed to get token"
  if [ -f token.json ]; then
    cat token.json
    rm -f token.json
  fi
  exit 1
fi
rm -f token.json

# Get a timetable entry
echo -e "\n1. Getting timetable entries..."
ENTRIES=$(curl -s -X GET "$BASE_URL/timetables/classes/1" \
  -H "Authorization: Bearer $TOKEN")

ENTRY_ID=$(echo "$ENTRIES" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null || echo "")

if [ -z "$ENTRY_ID" ]; then
  echo "No timetable entries found. Generating timetable first..."
  # Generate timetable
  curl -s -X POST "$BASE_URL/timetables/generate" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"class_id": 1}' | python3 -m json.tool
  
  sleep 2
  ENTRIES=$(curl -s -X GET "$BASE_URL/timetables/classes/1" \
    -H "Authorization: Bearer $TOKEN")
  ENTRY_ID=$(echo "$ENTRIES" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null || echo "")
fi

if [ -z "$ENTRY_ID" ]; then
  echo "Still no entries found"
  exit 1
fi

echo "Using entry ID: $ENTRY_ID"

# Get entry details to get version
ENTRY_DETAIL=$(curl -s -X GET "$BASE_URL/timetables/classes/1" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); entry=[e for e in data if e['id'] == $ENTRY_ID]; print(json.dumps(entry[0]) if entry else '{}')" 2>/dev/null || echo "{}")

VERSION=$(echo "$ENTRY_DETAIL" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 1))" 2>/dev/null || echo "1")

echo "Entry version: $VERSION"

# Update with correct version
echo -e "\n2. PATCH /timetables/entries/$ENTRY_ID (with correct version)"
UPDATE_RESPONSE=$(curl -s -X PATCH "$BASE_URL/timetables/entries/$ENTRY_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"room_id\": 1, \"version\": $VERSION}")

echo "$UPDATE_RESPONSE" | python3 -m json.tool

# Try to update with old version (should fail)
echo -e "\n3. PATCH /timetables/entries/$ENTRY_ID (with old version - should fail)"
OLD_VERSION=$((VERSION - 1))
ERROR_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X PATCH "$BASE_URL/timetables/entries/$ENTRY_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"room_id\": 2, \"version\": $OLD_VERSION}")

HTTP_CODE=$(echo "$ERROR_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$ERROR_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "409" ]; then
  echo "✓ Correctly returned 409 Conflict"
  echo "$BODY" | python3 -m json.tool
else
  echo "✗ Expected 409 Conflict, got $HTTP_CODE"
  echo "$BODY"
fi

echo -e "\n=== Optimistic Locking Tests Complete ==="
