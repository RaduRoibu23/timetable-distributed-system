#!/bin/bash

# 1. Obține tokenul
curl -s -X POST "http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=timetable-service" \
  -d "grant_type=password" \
  -d "username=radu" \
  -d "password=1234" > token.json

TOKEN=$(python3 - << 'EOF'
import json
with open("token.json") as f:
    data = json.load(f)
print(data["access_token"])
EOF
)

echo "Token obținut:"
echo $TOKEN

# 2. Testează apelul la backend
echo ""
echo "Testare GET /me"
curl -v -H "Authorization: Bearer $TOKEN" http://localhost:8000/me
echo ""
# Curatenie
rm token.json