#!/bin/bash

# Config Keycloak + backend
KC_TOKEN_URL="http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token"
CLIENT_ID="timetable-backend"
BACKEND_URL="http://localhost:8000"

# Funcție generică de test pentru un user
test_user() {
  local USERNAME="$1"
  local PASSWORD="$2"
  local LABEL="$3"

  echo "-----------------------------"
  echo "Testing $LABEL ($USERNAME)"

  # 1. Obține token de la Keycloak
  RESPONSE=$(curl -s -X POST "$KC_TOKEN_URL" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$CLIENT_ID" \
    -d "grant_type=password" \
    -d "username=$USERNAME" \
    -d "password=$PASSWORD")

  # IMPORTANT: nu mai folosim pipe + heredoc.
  # Pasăm JSON-ul prin variabila de mediu KC_RESPONSE.
  TOKEN=$(
    KC_RESPONSE="$RESPONSE" \
    python3 - << 'EOF'
import json, os
data_raw = os.environ.get("KC_RESPONSE", "")
try:
    data = json.loads(data_raw)
    token = data.get("access_token") or ""
    print(token)
except Exception:
    # Daca raspunsul nu e JSON valid sau nu contine access_token
    print("")
EOF
  )

  if [ -z "$TOKEN" ]; then
    echo "$LABEL FAIL: nu am putut obtine access_token din Keycloak"
    echo "Raspuns Keycloak:"
    echo "$RESPONSE"
    return 1
  fi

  # 2. Testează endpoint-ul /me
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$BACKEND_URL/me")

  if [ "$HTTP_CODE" = "200" ]; then
    echo "$LABEL OK"
    return 0
  else
    echo "$LABEL FAIL: /me a raspuns cu HTTP $HTTP_CODE"
    return 1
  fi
}

# Teste pentru fiecare rol
test_user "admin1"       "admin1"       "Admin"
test_user "professor1"        "professor1"        "Professor"
test_user "secretariat1" "secretariat1" "Secretariat"
test_user "student1"     "student1"     "Student"

echo "-----------------------------"
echo "Test complet."
