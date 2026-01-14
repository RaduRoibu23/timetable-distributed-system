#!/usr/bin/env bash
set -euo pipefail

KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
CLIENT_ID="timetable-backend"
BASE_URL="http://localhost:8000"

get_token() {
  local username="$1"
  local password="$2"
  curl -s -X POST "$KC_TOKEN_URL" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=${CLIENT_ID}" \
    -d "grant_type=password" \
    -d "username=${username}" \
    -d "password=${password}" > "token-${username}.json"

  python3 - << 'EOF' "token-${username}.json"
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
tok = data.get("access_token")
if not tok:
    print("ERROR_NO_TOKEN")
else:
    print(tok)
EOF
}

echo "=== Test Asynchronous Timetable Generation ==="
echo

echo "=== Token scheduler01 ==="
SCHEDULER_TOKEN="$(get_token scheduler01 scheduler01)"
if [[ "$SCHEDULER_TOKEN" == "ERROR_NO_TOKEN" ]]; then
  echo "Nu am putut lua token scheduler01"; cat token-scheduler01.json; exit 1
fi

echo
echo "=== POST /timetables/generate (async via RabbitMQ) ==="
GENERATE_RESPONSE="$(curl -s -X POST "${BASE_URL}/timetables/generate" \
  -H "Authorization: Bearer ${SCHEDULER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"class_id": 1}')"

echo "Response: ${GENERATE_RESPONSE}"

JOB_ID="$(echo "$GENERATE_RESPONSE" | python3 - << 'EOF'
import sys, json
try:
    data = json.load(sys.stdin)
    job_ids = data.get("job_ids", [])
    if job_ids:
        print(job_ids[0])
    else:
        print("0")
except:
    print("0")
EOF
)"

if [[ "$JOB_ID" == "0" ]]; then
  echo "EROARE: Nu am primit job_id"; exit 1
fi

echo "Job ID: ${JOB_ID}"

echo
echo "=== Waiting 5 seconds for job to process ==="
sleep 5

echo
echo "=== GET /timetables/jobs/${JOB_ID} (check status) ==="
JOB_STATUS="$(curl -s -X GET "${BASE_URL}/timetables/jobs/${JOB_ID}" \
  -H "Authorization: Bearer ${SCHEDULER_TOKEN}")"

echo "Job status: ${JOB_STATUS}"

STATUS="$(echo "$JOB_STATUS" | python3 - << 'EOF'
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get("status", "unknown"))
except:
    print("unknown")
EOF
)"

echo "Status: ${STATUS}"

if [[ "$STATUS" != "completed" && "$STATUS" != "processing" ]]; then
  echo "ATENTIE: Job status este ${STATUS}, asteptam completed sau processing"
fi

echo
echo "=== Verify timetable was generated ==="
TIMETABLE="$(curl -s -X GET "${BASE_URL}/timetables/classes/1" \
  -H "Authorization: Bearer ${SCHEDULER_TOKEN}")"

ENTRIES_COUNT="$(echo "$TIMETABLE" | python3 - << 'EOF'
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data) if isinstance(data, list) else 0)
except:
    print(0)
EOF
)"

echo "Timetable entries: ${ENTRIES_COUNT}"

if [[ "$ENTRIES_COUNT" == "35" ]]; then
  echo "✓ SUCCESS: Timetable generated with 35 entries"
else
  echo "ATENTIE: Expected 35 entries, got ${ENTRIES_COUNT}"
fi

echo
echo "=== Cleanup ==="
rm -f token-scheduler01.json

echo
echo "Test async generation completed!"
