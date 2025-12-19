#!/bin/bash

# Config Keycloak
KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
CLIENT_ID="timetable-backend"
USERNAME="admin1"
PASSWORD="admin1"

# 1. Obține tokenul
curl -s -X POST "$KC_TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "grant_type=password" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" > token.json

TOKEN=$(python3 - << 'EOF'
import json, sys
with open("token.json") as f:
    data = json.load(f)

token = data.get("access_token")
if not token:
    print("ERROR_NO_TOKEN")
    sys.exit(0)
print(token)
EOF
)

if [ "$TOKEN" = "ERROR_NO_TOKEN" ]; then
  echo "Nu am putut extrage access_token din raspunsul Keycloak:"
  cat token.json
  rm token.json
  exit 1
fi

echo "Token obtinut:"
echo "$TOKEN"

# 2. Testează apelul la backend
echo ""
echo "Testare GET /me"
curl -v -H "Authorization: Bearer $TOKEN" http://localhost:8000/me
echo ""

# Curatenie
rm token.json
