#!/bin/bash
# Test advanced validations (overlaps, capacity)

set -e

BASE_URL="http://localhost:8000"
TOKEN=""

echo "=== Testing Advanced Validations ==="

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

# Generate timetable first
echo -e "\n1. Generating timetable..."
curl -s -X POST "$BASE_URL/timetables/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"class_id": 1}' > /dev/null

sleep 2

# Get timetable entries
echo -e "\n2. Getting timetable entries..."
ENTRIES=$(curl -s -X GET "$BASE_URL/timetables/classes/1" \
  -H "Authorization: Bearer $TOKEN")

ENTRY_ID=$(echo "$ENTRIES" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null || echo "")

if [ -z "$ENTRY_ID" ]; then
  echo "No entries found"
  exit 1
fi

ENTRY_DETAIL=$(curl -s -X GET "$BASE_URL/timetables/classes/1" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); entry=[e for e in data if e['id'] == $ENTRY_ID]; print(json.dumps(entry[0]) if entry else '{}')" 2>/dev/null || echo "{}")

VERSION=$(echo "$ENTRY_DETAIL" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 1))" 2>/dev/null || echo "1")
TIMESLOT_ID=$(echo "$ENTRY_DETAIL" | python3 -c "import sys, json; print(json.load(sys.stdin).get('timeslot_id', ''))" 2>/dev/null || echo "")

echo "Entry ID: $ENTRY_ID, Timeslot ID: $TIMESLOT_ID, Version: $VERSION"

# Try to assign same room to another entry at same timeslot (should fail)
echo -e "\n3. Testing room overlap validation..."
OTHER_ENTRY=$(curl -s -X GET "$BASE_URL/timetables/classes/2" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); entry=[e for e in data if e.get('timeslot_id') == $TIMESLOT_ID]; print(json.dumps(entry[0]) if entry else '{}')" 2>/dev/null || echo "{}")

if [ "$OTHER_ENTRY" != "{}" ]; then
  OTHER_ENTRY_ID=$(echo "$OTHER_ENTRY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null || echo "")
  OTHER_VERSION=$(echo "$OTHER_ENTRY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 1))" 2>/dev/null || echo "1")
  
  # Get a room ID
  ROOMS=$(curl -s -X GET "$BASE_URL/rooms/" \
    -H "Authorization: Bearer $TOKEN")
  ROOM_ID=$(echo "$ROOMS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null || echo "")
  
  if [ ! -z "$ROOM_ID" ] && [ ! -z "$OTHER_ENTRY_ID" ]; then
    # Assign same room to entry 1
    curl -s -X PATCH "$BASE_URL/timetables/entries/$ENTRY_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"room_id\": $ROOM_ID, \"version\": $VERSION}" > /dev/null
    
    # Try to assign same room to other entry at same timeslot (should fail)
    ERROR_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X PATCH "$BASE_URL/timetables/entries/$OTHER_ENTRY_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"room_id\": $ROOM_ID, \"version\": $OTHER_VERSION}")
    
    HTTP_CODE=$(echo "$ERROR_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    BODY=$(echo "$ERROR_RESPONSE" | sed '/HTTP_CODE/d')
    
    if [ "$HTTP_CODE" = "400" ]; then
      echo "✓ Correctly returned 400 Bad Request for room overlap"
      echo "$BODY" | python3 -m json.tool
    else
      echo "✗ Expected 400 Bad Request, got $HTTP_CODE"
      echo "$BODY"
    fi
  fi
fi

echo -e "\n=== Advanced Validations Tests Complete ==="
