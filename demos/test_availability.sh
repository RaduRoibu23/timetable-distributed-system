#!/bin/bash
# Test availability endpoints

set -e

BASE_URL="http://localhost:8000"
TOKEN=""

echo "=== Testing Availability Endpoints ==="

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
echo "Token obtained"

# Test teacher availability
echo -e "\n1. Testing Teacher Availability..."

# Get teacher availability (should be empty initially)
echo "GET /teachers/1/availability"
curl -s -X GET "$BASE_URL/teachers/1/availability" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Create teacher availability
echo -e "\nPOST /teachers/1/availability"
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/teachers/1/availability" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"weekday": 0, "index_in_day": 1, "available": false}')

echo "$CREATE_RESPONSE" | python3 -m json.tool
AVAIL_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

# Update teacher availability
if [ ! -z "$AVAIL_ID" ]; then
  echo -e "\nPUT /teachers/1/availability/$AVAIL_ID"
  curl -s -X PUT "$BASE_URL/teachers/1/availability/$AVAIL_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"available": true}' | python3 -m json.tool
fi

# Test room availability
echo -e "\n2. Testing Room Availability..."

# Get room availability
echo "GET /rooms/1/availability"
curl -s -X GET "$BASE_URL/rooms/1/availability" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Create room availability
echo -e "\nPOST /rooms/1/availability"
ROOM_AVAIL_RESPONSE=$(curl -s -X POST "$BASE_URL/rooms/1/availability" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"weekday": 0, "index_in_day": 1, "available": false}')

echo "$ROOM_AVAIL_RESPONSE" | python3 -m json.tool
ROOM_AVAIL_ID=$(echo "$ROOM_AVAIL_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

# Update room availability
if [ ! -z "$ROOM_AVAIL_ID" ]; then
  echo -e "\nPUT /rooms/1/availability/$ROOM_AVAIL_ID"
  curl -s -X PUT "$BASE_URL/rooms/1/availability/$ROOM_AVAIL_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"available": true}' | python3 -m json.tool
fi

echo -e "\n=== Availability Tests Complete ==="
