# timetable-distributed-system (SCD)

Sistem distribuit pentru gestionarea orarelor (Timetable Management), cu autentificare/SSO prin Keycloak si backend REST in FastAPI.
---

## Status (pana acum)

Merge stabil pe Docker Compose:
- Keycloak + realm dedicat + client OIDC
- Seed automat: roluri + utilizatori fictivi (student/admin/professor/secretariat/scheduler/sysadmin)
- Backend FastAPI conectat la Postgres + endpoint-uri de baza (auth `/me`, lessons CRUD partial)
- Scripturi de demo/test (curl)

Docker Stack / Swarm:
- `docker-stack.yml` exista si a fost incercat, dar backend-ul nu se aliniaza complet cu restul stack-ului (WIP).

---

## Arhitectura (high-level)

- **Keycloak** (OIDC): emite JWT-uri, gestioneaza realm/roluri/useri
- **Postgres**: baza de date
- **timetable-management-service** (FastAPI): API REST (auth + entitati)

---

## Prerequisites

- Docker + Docker Compose
- (Optional) Python 3.10+ daca rulezi backend local

---

## Quickstart (Docker Compose)

### 1) Porneste infrastructura

Din root-ul repo-ului:

```bash
docker compose up -d
docker compose ps
```

Keycloak (local):
- http://localhost:8181

Swagger (backend):
- http://localhost:8000/docs

### 2) Seed Keycloak (realm + client + roluri + useri)

```bash
cd demos
chmod +x seed_keycloak.sh
./seed_keycloak.sh
```

Seed-ul:
- creeaza/actualizeaza realm-ul `timetable-realm`
- creeaza/actualizeaza client-ul `timetable-backend`
- creeaza roluri (realm roles): `admin`, `professor`, `student`, `secretariat`, `scheduler`, `sysadmin`
- creeaza utilizatori fictivi cu parole identice cu username-ul

### 3) Porneste backend-ul

#### Varianta A: backend in Docker (recomandat pentru demo)

Daca backend-ul e definit ca serviciu in `docker-compose.yml`:

```bash
cd ..
docker compose up -d timetable-management-service
docker compose ps
```

Daca nu esti sigur de numele serviciului:

```bash
docker compose config --services
```

#### Varianta B: backend local (folosind Keycloak + Postgres din compose)

```bash
cd services/timetable-management-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+psycopg2://keycloak:keycloak@localhost:5432/keycloak"
export KEYCLOAK_URL="http://localhost:8181"
export OIDC_ISSUER="http://localhost:8181/realms/timetable-realm"

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Utilizatori si roluri (seed)

### Username patterns
- studenti: `student01` .. `student50`
- profesori: `professor01` .. `professor10`
- admini: `admin01` .. `admin03`
- secretariat: `secretariat01` .. `secretariat02`
- scheduler (cei care se ocupa de orare): `scheduler01` .. `scheduler03`
- sysadmin: `sysadmin01`

### Parole
Parola este identica cu username-ul (exemplu):
- `student01 / student01`
- `admin02 / admin02`

---

## Scripturi de demo/test (`demos/`)

### Seed Keycloak
```bash
cd demos
./seed_keycloak.sh
```

### Auth test (obtinere token)
```bash
./test_auth.sh
```

### Test RBAC / roluri (smoke)
```bash
./test_all_roles.sh
```

### Lessons API tests
```bash
./test_lessons.sh
```

### Cauta user rapid in Keycloak (interactiv)
```bash
./find_user.sh
```

- selectezi tipul contului (student/admin/secretariat/professor/scheduler/sysadmin/uuid)
- scriptul afiseaza range-ul valid (ex: student 1-50)
- apoi afiseaza detalii user + rolurile de realm

---

## Endpoint-uri implementate (pana acum)

### Auth
- `GET /me` (JWT required)

### Lessons
- `POST /lessons` (JWT required)
- `GET /lessons` (JWT required)

Nota: accesul este protejat de `verify_token` (Keycloak JWT).

---

## Docker Stack / Swarm (WIP)

Exista fisierul `docker-stack.yml`, insa in acest moment:
- deploy-ul in Swarm porneste serviciile, dar backend-ul nu se conecteaza/nu se aliniaza complet (WIP)
- Compose ramane varianta recomandata pentru demo-ul curent

---

## Structura repo (relevant)

- `demos/` scripturi seed + teste
- `keycloak/realms/` configurari realm
- `services/timetable-management-service/` backend FastAPI
- `docker-compose.yml` rulare locala stabila
- `docker-stack.yml` WIP (Swarm)

---

## Roadmap (next)

- CRUD complet pentru Lessons (GET by id, update, delete)
- Entitati de baza: Rooms, Groups, Subjects, TimeSlots
- Timetable entries + validari suprapuneri (group/professor/room)
- Concurrency control pentru scheduler (optimistic lock / versioning sau DB lock)
- Audit log (optional, bun pentru demo)
