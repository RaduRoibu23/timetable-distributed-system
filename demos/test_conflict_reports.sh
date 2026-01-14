#!/bin/bash
# Test conflict reports endpoint

set -e

BASE_URL="http://localhost:8000"
TOKEN=""

echo "=== Testing Conflict Reports ==="

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

# Generate a timetable to create a job
echo -e "\n1. Generating timetable (creates a job)..."
JOB_RESPONSE=$(curl -s -X POST "$BASE_URL/timetables/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"class_id": 1}')

echo "$JOB_RESPONSE" | python3 -m json.tool

JOB_ID=$(echo "$JOB_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['job_ids'][0] if data.get('job_ids') else '')" 2>/dev/null || echo "")

if [ -z "$JOB_ID" ]; then
  echo "No job ID returned"
  exit 1
fi

echo "Job ID: $JOB_ID"

# Wait for job to complete
echo -e "\n2. Waiting for job to complete..."
sleep 3

# Get job status
echo -e "\n3. GET /timetables/jobs/$JOB_ID"
curl -s -X GET "$BASE_URL/timetables/jobs/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Get conflict reports
echo -e "\n4. GET /timetables/jobs/$JOB_ID/conflicts"
curl -s -X GET "$BASE_URL/timetables/jobs/$JOB_ID/conflicts" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n=== Conflict Reports Tests Complete ==="
