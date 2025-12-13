#!/usr/bin/env bash
set -euo pipefail

# -------- Config (override din env dacă vrei) --------
KEYCLOAK_BASE_URL="${KEYCLOAK_BASE_URL:-http://localhost:8181}"
MASTER_REALM="${MASTER_REALM:-master}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-admin}"

REALM="${REALM:-timetable-realm}"
CLIENT_ID="${CLIENT_ID:-timetable-backend}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# IMPORTANT:
# - UPDATE_PROFILE_IF_EXISTS=true => update firstName/lastName/email for existing users
# - RESET_PASSWORD_IF_EXISTS=false by default (set true dacă vrei să forțezi parola=username și la cei existenți)
UPDATE_PROFILE_IF_EXISTS="${UPDATE_PROFILE_IF_EXISTS:-true}"
RESET_PASSWORD_IF_EXISTS="${RESET_PASSWORD_IF_EXISTS:-false}"

# 2 => student01, 0 => student1 (eu recomand 2)
PAD_WIDTH="${PAD_WIDTH:-2}"

# Redirect URIs / Web Origins
REDIRECT_URIS=(
  "${BACKEND_URL}/*"
  "${BACKEND_URL}/docs/oauth2-redirect"
)
WEB_ORIGINS=(
  "${BACKEND_URL}"
)

# Counts
N_ADMINS=3
N_PROFESSORS=10
N_STUDENTS=50
N_SECRETARIAT=2
N_SCHEDULERS=3
N_SYSADMINS=1

# Roles (realm roles)
ROLES=(admin professor secretariat student scheduler sysadmin)
CREATE_REALM_IF_MISSING="${CREATE_REALM_IF_MISSING:-true}"

# -------- Name pools (fictive) --------
FIRST_NAMES=(Alina Andrei Bogdan Carmen Daria Daniel Elena Florin Gabriela George
             Iulia Ioana Irina Ionut Kevin Larisa Luca Mara Maria Mihai
             Nicolas Oana Paul Radu Raul Robert Sabina Stefan Teodora Tudor
             Valentina Vlad Bianca Catalin Ciprian Diana Eduard Fabian Horia
             Ilie Jasmina Karina Lavinia Marius Natalia Octavian Petrut Raluca
             Silviu Tiberiu Violeta Xenia Yannis Zara)

LAST_NAMES=(Matei Ionescu Popescu Dumitrescu Stan Petrescu Marinescu Radu Ilie
            Pavel Toma Dobre Tudor Enache Sandu Sava Neagu Cristea Voicu
            Mocanu Avram Barbu Gheorghiu Dragan Roman Stoica Pascu Nistor
            Oprea Serban Lupu Dumitrașcu Anghel Munteanu Rusu Coman Damian
            Jinga Vasile Moraru Chirila Simion Grigore Puscasu Manole Trifu)

# -------- Helpers --------
http_code() { curl -s -o /dev/null -w "%{http_code}" "$1"; }

kc_get() {
  curl -sS -H "Authorization: Bearer $TOKEN" "$1"
}

kc_json() {
  local method="$1"; shift
  local url="$1"; shift
  local data="${1:-}"
  curl -sS -X "$method" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "$url" \
    ${data:+-d "$data"}
}

wait_keycloak() {
  echo "Waiting for Keycloak at ${KEYCLOAK_BASE_URL} ..."
  for i in {1..60}; do
    if curl -sS "${KEYCLOAK_BASE_URL}/realms/${MASTER_REALM}" >/dev/null 2>&1; then
      echo "Keycloak is reachable."
      return 0
    fi
    sleep 2
  done
  echo "ERROR: Keycloak not reachable."
  exit 1
}

get_token() {
  local resp
  resp="$(curl -sS \
    -d "grant_type=password" \
    -d "client_id=admin-cli" \
    -d "username=${ADMIN_USER}" \
    -d "password=${ADMIN_PASS}" \
    "${KEYCLOAK_BASE_URL}/realms/${MASTER_REALM}/protocol/openid-connect/token")"

  TOKEN="$(printf '%s' "$resp" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')"
  if [[ -z "$TOKEN" ]]; then
    echo "ERROR: Could not obtain admin token. Response:"
    echo "$resp"
    exit 1
  fi
}

padN() {
  local n="$1"
  if [[ "$PAD_WIDTH" -le 0 ]]; then
    printf "%d" "$n"
  else
    printf "%0*d" "$PAD_WIDTH" "$n"
  fi
}

pick_name() {
  # deterministic: returns "First Last" for index i (1-based), with an offset per category
  local i="$1" offset="$2"
  python3 - <<PY
first_names=${#FIRST_NAMES[@]}
last_names=${#LAST_NAMES[@]}
i=int("$i")-1
offset=int("$offset")
fn_idx=(i+offset) % first_names
ln_idx=(i*3+offset) % last_names
print("${FIRST_NAMES[0]}")  # placeholder
PY
}

pick_first() {
  local i="$1" offset="$2"
  python3 - <<PY
FIRST=${#FIRST_NAMES[@]}
i=int("$i")-1
o=int("$offset")
print(${FIRST} and 0)
PY
}

# (fără dependențe, facem selecția direct în bash)
pick_first_bash() {
  local i="$1" offset="$2"
  local n="${#FIRST_NAMES[@]}"
  local idx=$(( ( (i-1) + offset ) % n ))
  echo "${FIRST_NAMES[$idx]}"
}
pick_last_bash() {
  local i="$1" offset="$2"
  local n="${#LAST_NAMES[@]}"
  local idx=$(( ( ( (i-1) * 3 ) + offset ) % n ))
  echo "${LAST_NAMES[$idx]}"
}

ensure_realm() {
  local code
  code="$(http_code "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}")"
  if [[ "$code" == "200" ]]; then
    echo "Realm '${REALM}' exists. Ensuring realm settings..."
    local current updated
    current="$(kc_get "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}")"
    CURRENT_REALM_JSON="$current" KEYCLOAK_BASE_URL="$KEYCLOAK_BASE_URL" REALM="$REALM" python3 - <<'PY' > /tmp/realm.json
import os, json
cur=json.loads(os.environ["CURRENT_REALM_JSON"])
desired={"realm": os.environ["REALM"], "enabled": True, "sslRequired": "external"}
cur.update(desired)
attrs = cur.get("attributes") or {}
attrs["frontendUrl"] = os.environ["KEYCLOAK_BASE_URL"]
cur["attributes"] = attrs
print(json.dumps(cur))
PY
    updated="$(cat /tmp/realm.json)"
    kc_json PUT "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}" "$updated" >/dev/null
    rm -f /tmp/realm.json
    return 0
  fi

  if [[ "$CREATE_REALM_IF_MISSING" != "true" ]]; then
    echo "ERROR: Realm '${REALM}' missing and CREATE_REALM_IF_MISSING=false"
    exit 1
  fi

  echo "Creating realm '${REALM}' ..."
  kc_json POST "${KEYCLOAK_BASE_URL}/admin/realms" \
    "$(KEYCLOAK_BASE_URL="$KEYCLOAK_BASE_URL" REALM="$REALM" python3 - <<'PY'
import os, json
print(json.dumps({
  "realm": os.environ["REALM"],
  "enabled": True,
  "sslRequired": "external",
  "attributes": {"frontendUrl": os.environ["KEYCLOAK_BASE_URL"]}
}))
PY
)" >/dev/null
}

ensure_role() {
  local role="$1"
  local code
  code="$(http_code "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/roles/${role}")"
  if [[ "$code" == "200" ]]; then
    return 0
  fi
  echo "Creating role '${role}' ..."
  kc_json POST "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/roles" "{\"name\":\"${role}\"}" >/dev/null
}

get_user_id() {
  local username="$1"
  kc_get "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users?username=${username}&exact=true" \
    | python3 -c 'import sys,json; arr=json.load(sys.stdin); print(arr[0]["id"] if arr else "")'
}

upsert_user() {
  local username="$1" password="$2" first="$3" last="$4" email="$5"
  local uid
  uid="$(get_user_id "$username")"

  if [[ -z "$uid" ]]; then
    echo "Creating user '${username}' (${first} ${last}, ${email}) ..."
    kc_json POST "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users" \
      "$(USERNAME="$username" FIRST="$first" LAST="$last" EMAIL="$email" python3 - <<'PY'
import os, json
print(json.dumps({
  "username": os.environ["USERNAME"],
  "enabled": True,
  "emailVerified": True,
  "firstName": os.environ["FIRST"],
  "lastName": os.environ["LAST"],
  "email": os.environ["EMAIL"],
}))
PY
)" >/dev/null

    uid="$(get_user_id "$username")"
    if [[ -z "$uid" ]]; then
      echo "ERROR: Could not fetch id for created user '${username}'"
      exit 1
    fi

    echo "Setting password for '${username}' ..."
    kc_json PUT "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users/${uid}/reset-password" \
      "{\"type\":\"password\",\"temporary\":false,\"value\":\"${password}\"}" >/dev/null
    return 0
  fi

  # User exists: update profile if requested
  if [[ "$UPDATE_PROFILE_IF_EXISTS" == "true" ]]; then
    echo "Updating profile for existing user '${username}' ..."
    local current updated
    current="$(kc_get "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users/${uid}")"
    updated="$(CURRENT_USER_JSON="$current" FIRST="$first" LAST="$last" EMAIL="$email" python3 - <<'PY'
import os, json
u=json.loads(os.environ["CURRENT_USER_JSON"])
u["firstName"]=os.environ["FIRST"]
u["lastName"]=os.environ["LAST"]
u["email"]=os.environ["EMAIL"]
u["enabled"]=True
u["emailVerified"]=True
print(json.dumps(u))
PY
)"
    kc_json PUT "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users/${uid}" "$updated" >/dev/null
  fi

  # Reset password if requested
  if [[ "$RESET_PASSWORD_IF_EXISTS" == "true" ]]; then
    echo "Resetting password for existing user '${username}' ..."
    kc_json PUT "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users/${uid}/reset-password" \
      "{\"type\":\"password\",\"temporary\":false,\"value\":\"${password}\"}" >/dev/null
  fi
}

get_role_id() {
  local role="$1"
  kc_get "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/roles/${role}" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])'
}

user_has_role() {
  local uid="$1" role="$2"
  kc_get "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users/${uid}/role-mappings/realm" \
    | python3 -c 'import sys,json; role=sys.argv[1]; arr=json.load(sys.stdin); print("yes" if any(x.get("name")==role for x in arr) else "no")' "$role"
}

assign_realm_role() {
  local username="$1" role="$2"
  local uid rid has
  uid="$(get_user_id "$username")"
  rid="$(get_role_id "$role")"
  has="$(user_has_role "$uid" "$role")"
  if [[ "$has" == "yes" ]]; then
    return 0
  fi
  echo "Assigning role '${role}' to '${username}' ..."
  kc_json POST "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users/${uid}/role-mappings/realm" \
    "[{\"id\":\"${rid}\",\"name\":\"${role}\"}]" >/dev/null
}

json_array_from_args() {
  python3 - "$@" <<'PY'
import sys, json
print(json.dumps(sys.argv[1:]))
PY
}

get_client_internal_id() {
  local client_id="$1"
  kc_get "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/clients?clientId=${client_id}" \
    | python3 -c 'import sys,json; arr=json.load(sys.stdin); print(arr[0]["id"] if arr else "")'
}

ensure_client_timetable_backend() {
  local internal_id redirect_json origins_json desired update_payload current

  redirect_json="$(json_array_from_args "${REDIRECT_URIS[@]}")"
  origins_json="$(json_array_from_args "${WEB_ORIGINS[@]}")"

  desired="$(REDIRECT_URIS_JSON="$redirect_json" WEB_ORIGINS_JSON="$origins_json" BACKEND_URL="$BACKEND_URL" CLIENT_ID="$CLIENT_ID" python3 - <<'PY'
import os, json
redirect_uris=json.loads(os.environ["REDIRECT_URIS_JSON"])
web_origins=json.loads(os.environ["WEB_ORIGINS_JSON"])
obj = {
  "clientId": os.environ["CLIENT_ID"],
  "protocol": "openid-connect",
  "publicClient": True,
  "directAccessGrantsEnabled": True,
  "standardFlowEnabled": True,
  "implicitFlowEnabled": False,
  "serviceAccountsEnabled": False,
  "rootUrl": os.environ["BACKEND_URL"],
  "baseUrl": os.environ["BACKEND_URL"],
  "redirectUris": redirect_uris,
  "webOrigins": web_origins,
  "bearerOnly": False,
}
print(json.dumps(obj))
PY
)"

  internal_id="$(get_client_internal_id "$CLIENT_ID")"

  if [[ -z "$internal_id" ]]; then
    echo "Creating client '${CLIENT_ID}' ..."
    kc_json POST "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/clients" "$desired" >/dev/null
    return 0
  fi

  echo "Updating client '${CLIENT_ID}' settings ..."
  current="$(kc_get "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/clients/${internal_id}")"
  update_payload="$(CURRENT_CLIENT_JSON="$current" DESIRED_JSON="$desired" python3 - <<'PY'
import os, json
cur=json.loads(os.environ["CURRENT_CLIENT_JSON"])
desired=json.loads(os.environ["DESIRED_JSON"])
cur.update(desired)
print(json.dumps(cur))
PY
)"
  kc_json PUT "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/clients/${internal_id}" "$update_payload" >/dev/null
}

# -------- Create all users --------
create_category() {
  local prefix="$1" role="$2" count="$3" offset="$4"
  local i u fn ln email
  for i in $(seq 1 "$count"); do
    u="${prefix}$(padN "$i")"
    fn="$(pick_first_bash "$i" "$offset")"
    ln="$(pick_last_bash "$i" "$offset")"
    email="${u}@timetable.local"
    upsert_user "$u" "$u" "$fn" "$ln" "$email"
    assign_realm_role "$u" "$role"
  done
}

# -------- Run --------
wait_keycloak
get_token

ensure_realm

for r in "${ROLES[@]}"; do
  ensure_role "$r"
done

ensure_client_timetable_backend

echo "Creating/updating users..."
create_category "admin"       "admin"       "$N_ADMINS"      0
create_category "professor"   "professor"   "$N_PROFESSORS"  7
create_category "secretariat" "secretariat" "$N_SECRETARIAT" 13
create_category "scheduler"   "scheduler"   "$N_SCHEDULERS"  19
create_category "sysadmin"    "sysadmin"    "$N_SYSADMINS"   23
create_category "student"     "student"     "$N_STUDENTS"    31

echo "Done. Seed completed for realm '${REALM}' and client '${CLIENT_ID}'."
echo "Note:"
echo "  - Password = username (ex: student01/student01)"
echo "  - Existing users are updated if UPDATE_PROFILE_IF_EXISTS=true"
echo "  - Existing passwords are reset only if RESET_PASSWORD_IF_EXISTS=true"
