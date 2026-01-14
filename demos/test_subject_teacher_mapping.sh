#!/bin/bash
# Test subject-teacher mapping endpoints

set -e

BASE_URL="http://localhost:8000"
TOKEN=""

echo "=== Testing Subject-Teacher Mapping ==="

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

# Get subjects
echo -e "\n1. Getting subjects..."
SUBJECTS=$(curl -s -X GET "$BASE_URL/subjects" \
  -H "Authorization: Bearer $TOKEN")
SUBJECT_ID=$(echo "$SUBJECTS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null || echo "")

if [ -z "$SUBJECT_ID" ]; then
  echo "No subjects found"
  exit 1
fi

echo "Using subject ID: $SUBJECT_ID"

# Get teachers for subject
echo -e "\n2. GET /subjects/$SUBJECT_ID/teachers"
curl -s -X GET "$BASE_URL/subjects/$SUBJECT_ID/teachers" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Get classes
echo -e "\n3. Getting classes..."
CLASSES=$(curl -s -X GET "$BASE_URL/classes" \
  -H "Authorization: Bearer $TOKEN")
CLASS_ID=$(echo "$CLASSES" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null || echo "")

if [ -z "$CLASS_ID" ]; then
  echo "No classes found"
  exit 1
fi

echo "Using class ID: $CLASS_ID"

# Assign teacher to subject
echo -e "\n4. POST /subjects/$SUBJECT_ID/teachers (assign teacher 1 to class $CLASS_ID)"
ASSIGN_RESPONSE=$(curl -s -X POST "$BASE_URL/subjects/$SUBJECT_ID/teachers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"class_id\": $CLASS_ID, \"teacher_id\": 1}")

echo "$ASSIGN_RESPONSE" | python3 -m json.tool

# Get teachers for subject again
echo -e "\n5. GET /subjects/$SUBJECT_ID/teachers (after assignment)"
curl -s -X GET "$BASE_URL/subjects/$SUBJECT_ID/teachers" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Remove teacher assignment
echo -e "\n6. DELETE /subjects/$SUBJECT_ID/teachers/1?class_id=$CLASS_ID"
curl -s -X DELETE "$BASE_URL/subjects/$SUBJECT_ID/teachers/1?class_id=$CLASS_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n=== Subject-Teacher Mapping Tests Complete ==="
