#!/usr/bin/env bash
set -euo pipefail

KEYCLOAK_BASE_URL="${KEYCLOAK_BASE_URL:-http://localhost:8181}"
MASTER_REALM="${MASTER_REALM:-master}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-admin}"
REALM="${REALM:-timetable-realm}"

PAD_WIDTH="${PAD_WIDTH:-2}" # 2 => student03 ; 0 => student3

# Range-uri conforme seed-ului
RANGE_STUDENT_MAX="${RANGE_STUDENT_MAX:-50}"
RANGE_ADMIN_MAX="${RANGE_ADMIN_MAX:-3}"
RANGE_SECRETARIAT_MAX="${RANGE_SECRETARIAT_MAX:-2}"
RANGE_PROFESSOR_MAX="${RANGE_PROFESSOR_MAX:-10}"
RANGE_SCHEDULER_MAX="${RANGE_SCHEDULER_MAX:-3}"
RANGE_SYSADMIN_MAX="${RANGE_SYSADMIN_MAX:-1}"

# ---------------- Helpers ----------------
is_uuid() {
  local s="$1"
  [[ "$s" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]
}

padN() {
  local n="$1"
  if [[ "$PAD_WIDTH" -le 0 ]]; then
    printf "%d" "$n"
  else
    printf "%0*d" "$PAD_WIDTH" "$n"
  fi
}

kc_get() {
  local url="$1"
  local resp
  resp="$(curl -sS -H "Authorization: Bearer ${TOKEN}" -w $'\n%{http_code}' "$url")"
  RESP_CODE="${resp##*$'\n'}"
  RESP_BODY="${resp%$'\n'*}"
}

die_http() {
  local ctx="$1"
  echo "ERROR: ${ctx} (HTTP ${RESP_CODE})"
  echo "Response (first 30 lines):"
  printf '%s\n' "$RESP_BODY" | sed -n '1,30p'
  exit 1
}

get_admin_token() {
  local resp
  resp="$(curl -sS \
    -d "grant_type=password" \
    -d "client_id=admin-cli" \
    -d "username=${ADMIN_USER}" \
    -d "password=${ADMIN_PASS}" \
    "${KEYCLOAK_BASE_URL}/realms/${MASTER_REALM}/protocol/openid-connect/token")"

  TOKEN="$(printf '%s' "$resp" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null || true)"

  if [[ -z "${TOKEN}" ]]; then
    echo "ERROR: Could not obtain access_token. Response:"
    printf '%s\n' "$resp" | sed -n '1,60p'
    exit 1
  fi
}

get_user_id_by_username() {
  local username="$1"
  kc_get "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users?username=${username}&exact=true"
  [[ "$RESP_CODE" == "200" ]] || die_http "Search user username='${username}'"

  printf '%s' "$RESP_BODY" | python3 -c 'import sys,json; a=json.load(sys.stdin); print(a[0]["id"] if a else "")'
}

print_user_details() {
  local uid="$1"
  kc_get "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users/${uid}"
  [[ "$RESP_CODE" == "200" ]] || die_http "Get user details id='${uid}'"

  printf '%s' "$RESP_BODY" | python3 -c '
import sys,json,datetime
u=json.load(sys.stdin)
def ts(ms):
  if ms is None: return "-"
  return datetime.datetime.fromtimestamp(ms/1000).isoformat(sep=" ", timespec="seconds")
uid=u.get("id","-")
username=u.get("username","-")
first=u.get("firstName") or ""
last=u.get("lastName") or ""
name=(first+" "+last).strip() or "-"
email=u.get("email","-")
enabled=u.get("enabled","-")
created=ts(u.get("createdTimestamp"))
print("User:")
print("  id:        {}".format(uid))
print("  username:  {}".format(username))
print("  name:      {}".format(name))
print("  email:     {}".format(email))
print("  enabled:   {}".format(enabled))
print("  created:   {}".format(created))
'
}

print_roles() {
  local uid="$1"
  kc_get "${KEYCLOAK_BASE_URL}/admin/realms/${REALM}/users/${uid}/role-mappings/realm"
  [[ "$RESP_CODE" == "200" ]] || die_http "Get realm roles id='${uid}'"

  printf '%s' "$RESP_BODY" | python3 -c '
import sys,json
arr=json.load(sys.stdin)
names=sorted([x.get("name","") for x in arr if x.get("name")])
print("Realm roles:")
if not names:
  print("  (none)")
else:
  for n in names:
    print("  - {}".format(n))
'
}

print_user_details_and_roles() {
  local uid="$1"
  print_user_details "$uid"
  print_roles "$uid"
}

find_by_username_with_fallback() {
  local u1="$1" u2="$2"
  local uid

  uid="$(get_user_id_by_username "$u1")"
  if [[ -n "$uid" ]]; then
    print_user_details_and_roles "$uid"
    return 0
  fi

  echo "Not found '${u1}'. Trying '${u2}' ..."
  uid="$(get_user_id_by_username "$u2")"
  if [[ -n "$uid" ]]; then
    print_user_details_and_roles "$uid"
    return 0
  fi

  echo "Not found: '${u1}' or '${u2}' in realm '${REALM}'."
  exit 1
}

prompt_id_in_range() {
  local label="$1" max="$2"
  local id

  echo "" >&2
  echo "Range valid pentru ${label}: 1-${max}" >&2

  while true; do
    read -r -p "Da-mi ID-ul (1-${max}) sau UUID: " id >&2

    if is_uuid "$id"; then
      echo "$id"
      return 0
    fi

    if [[ "$id" =~ ^[0-9]+$ ]] && (( id >= 1 && id <= max )); then
      echo "$id"
      return 0
    fi

    echo "Input invalid. Introdu un numar in range (1-${max}) sau un UUID valid." >&2
  done
}


# ---------------- Main ----------------
get_admin_token

echo "Keycloak: ${KEYCLOAK_BASE_URL}"
echo "Realm:    ${REALM}"
echo "Pad width: ${PAD_WIDTH} (2 => student03, 0 => student3)"
echo

echo "Alege tip cont:"
echo "  1) student      (1-${RANGE_STUDENT_MAX})"
echo "  2) admin        (1-${RANGE_ADMIN_MAX})"
echo "  3) secretariat  (1-${RANGE_SECRETARIAT_MAX})"
echo "  4) professor    (1-${RANGE_PROFESSOR_MAX})"
echo "  5) scheduler    (1-${RANGE_SCHEDULER_MAX})"
echo "  6) sysadmin     (1-${RANGE_SYSADMIN_MAX})"
echo "  7) uuid (am deja Keycloak user id)"
echo
read -r -p "Optiune (1-7): " opt

case "$opt" in
  1) prefix="student";     max="$RANGE_STUDENT_MAX";     label="student" ;;
  2) prefix="admin";       max="$RANGE_ADMIN_MAX";       label="admin" ;;
  3) prefix="secretariat"; max="$RANGE_SECRETARIAT_MAX"; label="secretariat" ;;
  4) prefix="professor";   max="$RANGE_PROFESSOR_MAX";   label="professor" ;;
  5) prefix="scheduler";   max="$RANGE_SCHEDULER_MAX";   label="scheduler" ;;
  6) prefix="sysadmin";    max="$RANGE_SYSADMIN_MAX";    label="sysadmin" ;;
  7) prefix="uuid";        max="0";                      label="uuid" ;;
  *) echo "Optiune invalida."; exit 1 ;;
esac

if [[ "$prefix" == "uuid" ]]; then
  echo
  read -r -p "Da-mi UUID-ul Keycloak user id: " uid
  is_uuid "$uid" || { echo "ERROR: input-ul nu arata ca UUID."; exit 1; }
  print_user_details_and_roles "$uid"
  exit 0
fi

id="$(prompt_id_in_range "$label" "$max")"

# dacă utilizatorul a introdus UUID chiar aici
if is_uuid "$id"; then
  print_user_details_and_roles "$id"
  exit 0
fi

u1="${prefix}$(padN "$id")"
u2="${prefix}${id}"

echo
echo "Caut username: ${u1}"
find_by_username_with_fallback "$u1" "$u2"
