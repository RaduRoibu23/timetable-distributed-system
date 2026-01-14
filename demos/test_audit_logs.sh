#!/bin/bash
# Test audit logs endpoint

set -e

BASE_URL="http://localhost:8000"
TOKEN=""

echo "=== Testing Audit Logs Endpoint ==="

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

# Generate some activity first
echo -e "\n1. Generating activity (create a room)..."
curl -s -X POST "$BASE_URL/rooms/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Room Audit", "capacity": 30}' > /dev/null

sleep 1

# Get all audit logs
echo -e "\n2. GET /audit-logs"
curl -s -X GET "$BASE_URL/audit-logs" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -20

# Get audit logs with pagination
echo -e "\n3. GET /audit-logs?limit=5&offset=0"
curl -s -X GET "$BASE_URL/audit-logs?limit=5&offset=0" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Get audit logs filtered by action
echo -e "\n4. GET /audit-logs?action=timetable_generated"
curl -s -X GET "$BASE_URL/audit-logs?action=timetable_generated" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -10

# Test with student (should fail)
echo -e "\n5. Testing RBAC (student should not access)..."
curl -s -X POST "$KC_TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "grant_type=password" \
  -d "username=student01" \
  -d "password=student01" > student_token.json

STUDENT_TOKEN=$(python3 - << 'EOF'
import json, sys
try:
    with open("student_token.json") as f:
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
rm -f student_token.json

if [ ! -z "$STUDENT_TOKEN" ]; then
  ERROR_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "$BASE_URL/audit-logs" \
    -H "Authorization: Bearer $STUDENT_TOKEN")
  
  HTTP_CODE=$(echo "$ERROR_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
  if [ "$HTTP_CODE" = "403" ]; then
    echo "✓ Correctly returned 403 Forbidden for student"
  else
    echo "✗ Expected 403 Forbidden, got $HTTP_CODE"
  fi
fi

echo -e "\n=== Audit Logs Tests Complete ==="
