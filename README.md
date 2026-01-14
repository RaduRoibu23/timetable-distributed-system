# Timetable Distributed System

Sistem distribuit pentru managementul orarelor școlare, dezvoltat ca proiect pentru cursul de Sisteme Distribuite (SCD). Proiectul implementează un backend FastAPI cu autentificare Keycloak, control acces bazat pe roluri (RBAC), generare automată de orare și notificări.

## 🏗️ Arhitectură

Sistemul este orchestrat cu **Docker Swarm** și include următoarele componente:

- **Keycloak** (port 8181) - Management identitate și autentificare OIDC
- **PostgreSQL** - Baza de date pentru Keycloak și backend
- **RabbitMQ** (ports 5672, 15672) - Broker de mesaje pentru procesare asincronă
- **FastAPI Backend** (port 8000) - API REST pentru managementul orarelor
- **Scheduling Engine Service** - Worker pentru generare asincronă de orare (scalabil orizontal)
- **Frontend Static** (port 3000) - Interfață web demo

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│   Keycloak   │────▶│  PostgreSQL │
│  (Browser)  │     │  (Auth/OIDC) │     │   (Storage) │
└─────────────┘     └──────────────┘     └─────────────┘
      │                     │
      │                     │
      ▼                     ▼
┌─────────────┐     ┌──────────────┐
│  Frontend   │────▶│  FastAPI     │
│  (Nginx)    │     │  Backend     │
└─────────────┘     └──────────────┘
                           │
                           ├─────────────┐
                           │             │
                           ▼             ▼
                    ┌─────────────┐  ┌──────────────┐
                    │  PostgreSQL │  │   RabbitMQ   │
                    │  (App Data) │  │  (Message    │
                    └─────────────┘  │   Broker)    │
                                     └──────────────┘
                                            │
                                            │ (consumes jobs)
                                            ▼
                                     ┌──────────────┐
                                     │  Scheduling  │
                                     │  Engine      │
                                     │  (Workers)    │
                                     └──────────────┘
                                            │
                                            ▼
                                     ┌─────────────┐
                                     │  PostgreSQL │
                                     │  (App Data) │
                                     └─────────────┘
```

## ✨ Features Implementate

### 🔐 Autentificare și Autorizare
- ✅ Integrare Keycloak cu realm dedicat (`timetable-realm`)
- ✅ Verificare JWT tokens pentru toate endpoint-urile
- ✅ **RBAC (Role-Based Access Control)** implementat:
  - `student` - poate vedea doar orarul clasei sale
  - `professor` - poate vedea orarul și trimite notificări
  - `secretariat` - poate publica orarul și trimite notificări
  - `scheduler` - poate genera/modifica orare
  - `admin` / `sysadmin` - acces complet

### 📚 Model de Date
- ✅ **SchoolClass** - Clase școlare (ex: IX-A, IX-B)
- ✅ **Subject** - Materii de învățământ
- ✅ **TimeSlot** - Sloturi temporale (5 zile × 7 ore = 35 sloturi/săptămână)
- ✅ **Curriculum** - Plan de învățământ (ore/săptămână per materie și clasă)
- ✅ **TimetableEntry** - Intrări în orar (clasă + slot → materie)
- ✅ **UserProfile** - Mapare username → clasă (pentru studenți)
- ✅ **Notification** - Notificări pentru utilizatori
- ✅ Constrângeri DB: `UNIQUE(class_id, timeslot_id)` pentru a preveni suprapuneri

### 🌱 Seed Automat
- ✅ Seed la startup pentru date demo:
  - 2 clase: `IX-A`, `IX-B`
  - 35 time slots (Luni-Vineri, ore 1-7)
  - 13 materii (Română, Matematică, Informatică, Fizică, Chimie, etc.)
  - Curriculum complet (35 ore/săptămână per clasă)
  - UserProfile pentru `student01` → IX-A

### 📡 API Endpoints

#### Autentificare
- `GET /me` - Informații utilizator curent (username, roles, class_id)

#### Catalog (CRUD complet)
- `GET /classes` - Listează toate clasele
- `POST /classes` - Creează clasă (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /classes/{id}` - Actualizează clasă (RBAC: `secretariat`, `admin`, `sysadmin`)
- `DELETE /classes/{id}` - Șterge clasă (RBAC: `secretariat`, `admin`, `sysadmin`)
- `GET /subjects` - Listează toate materiile
- `POST /subjects` - Creează materie (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /subjects/{id}` - Actualizează materie (RBAC: `secretariat`, `admin`, `sysadmin`)
- `DELETE /subjects/{id}` - Șterge materie (RBAC: `secretariat`, `admin`, `sysadmin`)
- `GET /curricula` - Listează curriculum-urile (toate rolurile)
- `POST /curricula` - Creează curriculum (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /curricula/{id}` - Actualizează curriculum (RBAC: `secretariat`, `admin`, `sysadmin`)
- `DELETE /curricula/{id}` - Șterge curriculum (RBAC: `secretariat`, `admin`, `sysadmin`)
- `GET /timeslots` - Listează toate sloturile temporale (read-only)

#### Orar (Timetables)
- `POST /timetables/generate` - Generează orar asincron pentru una sau mai multe clase (via RabbitMQ)
  - **RBAC**: `scheduler`, `secretariat`, `admin`, `sysadmin`
  - Body: `{"class_id": 1}` sau `{"class_ids": [1, 2]}`
  - Returnează: `{"job_ids": [1, 2], "message": "..."}`
  - Job-urile sunt procesate asincron de Scheduling Engine Service
- `GET /timetables/jobs/{job_id}` - Verifică statusul unui job de generare
  - Returnează: `{"id": 1, "status": "pending|processing|completed|failed", ...}`
- `GET /timetables/classes/{class_id}` - Obține orarul unei clase
- `GET /timetables/me` - Obține orarul utilizatorului curent
  - **Student**: returnează automat orarul clasei sale (ignoră parametri)
  - **Alte roluri**: pot specifica `?class_id=X`
- `PATCH /timetables/entries/{id}` - Editează manual o intrare din orar
  - **RBAC**: `secretariat`, `admin`, `sysadmin`
  - Body: `{"subject_id": 2}` sau `{"room_id": 3}` sau ambele

#### Notificări
- `POST /notifications/send` - Trimite notificare către utilizator sau clasă
  - **RBAC**: `secretariat`, `admin`, `sysadmin`, `professor`
  - Body: `{"user_id": 1}` sau `{"class_id": 1}`, `{"message": "..."}`
- `GET /notifications/me` - Listează notificările utilizatorului curent
- `PATCH /notifications/{id}/read` - Marchează notificarea ca citită

#### Compatibilitate Frontend (Alias-uri)
- `POST /schedule/run` - Alias pentru `POST /timetables/generate` (pentru frontend)
- `GET /lessons/mine` - Alias pentru `GET /timetables/me` (pentru frontend)
- `GET /users` - Returnează `[]` (compatibilitate admin actions)

#### Rooms (Săli)
- `GET /rooms` - Listează sălile
- `POST /rooms` - Creează sală (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /rooms/{id}` - Actualizează sală (RBAC: `secretariat`, `admin`, `sysadmin`)
- `DELETE /rooms/{id}` - Șterge sală (RBAC: `secretariat`, `admin`, `sysadmin`)

#### Lessons (Legacy - pentru compatibilitate)
- `GET /lessons` - Listează lecțiile
- `POST /lessons` - Creează lecție (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /lessons/{id}` - Actualizează lecție
- `DELETE /lessons/{id}` - Șterge lecție

### 🤖 Generator de Orar
- ✅ Algoritm de generare automată:
  - Respectă `hours_per_week` din curriculum
  - Maxim 2 ore de aceeași materie pe zi (soft constraint)
  - Generează exact 35 intrări per clasă (5×7)
  - Idempotent: regenerează complet orarul la fiecare apel
- ✅ **Generare asincronă**:
  - Job-urile sunt publicate în RabbitMQ
  - Scheduling Engine Service procesează job-urile în paralel (scalabil orizontal)
  - Status tracking pentru fiecare job
  - Notificări automate după generare

## 🚀 Quick Start

### Prerequisites
- Docker Engine cu suport Swarm
- Docker Desktop (pe Windows) sau Docker Engine pe Linux
- WSL2 (recomandat pe Windows)

### Setup

1. **Inițializează Docker Swarm** (dacă nu e deja activ):
```bash
docker swarm init
```

2. **Deploy stack-ul**:
```bash
docker stack deploy -c docker-stack.yml scd
```

3. **Verifică serviciile**:
```bash
docker stack services scd
```

Așteaptă câteva secunde până toate serviciile ajung în starea `1/1` (Running).

4. **Accesează serviciile**:
- Keycloak Admin: http://localhost:8181 (admin/admin)
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs (Swagger): http://localhost:8000/docs

### Utilizatori Demo

Toți utilizatorii au parola identică cu username-ul:

| Username | Rol | Descriere |
|----------|-----|-----------|
| `student01` | student | Student în clasa IX-A |
| `professor01` | professor | Profesor |
| `secretariat01` | secretariat | Personal secretariat |
| `scheduler01` | scheduler | Planificator orare |
| `admin01` | admin | Administrator |
| `sysadmin01` | sysadmin | Super administrator |

## 🧪 Testare

Proiectul include scripturi de test în directorul `demos/`:

### Test RBAC
Verifică că studentul primește 403 la operații privilegiate:
```bash
bash demos/test_rbac.sh
```

### Test Seed
Verifică că datele demo au fost create corect:
```bash
bash demos/test_seed.sh
```

### Test Timetable (Student Access)
Verifică că studentul vede doar orarul clasei sale:
```bash
bash demos/test_timetable_me.sh
```

### Test Autentificare
Testează obținerea token și apelul `/me`:
```bash
bash demos/test_auth.sh
```

## 📁 Structură Proiect

```
timetable-distributed-system/
├── docker-stack.yml              # Configurație Docker Swarm
├── build-images.sh               # Script pentru build imagini Docker
├── keycloak/
│   └── realms/
│       └── timetable-realm.json # Configurație realm Keycloak (import automat)
├── services/
│   ├── timetable-management-service/
│   │   ├── app/
│   │   │   ├── api/              # Endpoint-uri FastAPI
│   │   │   │   ├── routes_auth.py
│   │   │   │   ├── routes_rooms.py
│   │   │   │   ├── routes_lessons.py
│   │   │   │   ├── routes_catalog_read.py
│   │   │   │   ├── routes_timetables.py
│   │   │   │   ├── routes_notifications.py
│   │   │   │   └── routes_compat.py
│   │   │   ├── core/             # Configurație și securitate
│   │   │   │   ├── config.py
│   │   │   │   ├── security.py
│   │   │   │   └── rbac.py       # RBAC dependency
│   │   │   ├── services/         # Logică business
│   │   │   │   ├── timetable_generator.py
│   │   │   │   ├── notifications.py
│   │   │   │   ├── rabbitmq_client.py
│   │   │   │   └── audit.py
│   │   │   ├── models.py         # Modele SQLAlchemy
│   │   │   ├── db.py             # Configurație DB
│   │   │   ├── init_db.py        # Seed automat
│   │   │   └── main.py           # Entry point FastAPI
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── scheduling-engine-service/
│   │   ├── app/
│   │   │   └── main.py           # Worker pentru generare asincronă
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── frontend/                 # Frontend static (demo)
│       ├── app.js
│       ├── index.html
│       ├── styles.css
│       ├── config.js
│       ├── nginx.conf
│       └── Dockerfile
├── demos/                        # Scripturi de test
│   ├── test_auth.sh
│   ├── test_rbac.sh
│   ├── test_seed.sh
│   ├── test_timetable_me.sh
│   ├── test_notifications.sh
│   ├── test_rooms.sh
│   ├── test_lessons.sh
│   ├── test_catalog_crud.sh
│   ├── test_timetable_patch.sh
│   ├── test_async_generation.sh
│   ├── test_all_roles.sh
│   ├── test_frontend_compat.sh
│   ├── seed_keycloak.sh
│   └── find_user.sh
└── README.md
```

## 🔒 Permisiuni pe Roluri

| Acțiune | student | professor | secretariat | scheduler | admin | sysadmin |
|---------|---------|-----------|-------------|-----------|-------|----------|
| Vezi orarul clasei sale | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Vezi orarul altor clase | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Generează orar | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Modifică orar | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Publică orar | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Trimite notificări | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ |
| CRUD Rooms/Lessons | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| CRUD Catalog | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |

## 📝 Exemple de Utilizare API

### Obținere Token
```bash
curl -X POST "http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=timetable-backend" \
  -d "grant_type=password" \
  -d "username=student01" \
  -d "password=student01"
```

### Generează Orar (ca sysadmin)
```bash
TOKEN="<your-token>"
curl -X POST "http://localhost:8000/timetables/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"class_id": 1}'
```

### Vezi Orarul Meu (ca student)
```bash
TOKEN="<student-token>"
curl "http://localhost:8000/timetables/me" \
  -H "Authorization: Bearer $TOKEN"
```

## 🛠️ Dezvoltare

### Build Images
Pentru a construi imaginile Docker pentru serviciile custom:
```bash
bash build-images.sh
```

Aceasta va construi:
- `roiburadu/timetable-management-service:dev1`
- `roiburadu/scheduling-engine-service:dev1`

**Notă**: Frontend-ul (`roiburadu/timetable-frontend:dev`) trebuie construit manual:
```bash
cd services/frontend
docker build -t roiburadu/timetable-frontend:dev .
```

### Rebuild Services (după modificări)
```bash
# Backend
docker service update --force scd_timetable_backend

# Frontend
docker service update --force scd_timetable_frontend

# Scheduling Engine
docker service update --force scd_scheduling_engine
```

### Logs
```bash
# Logs backend
docker service logs -f scd_timetable_backend

# Logs Keycloak
docker service logs -f scd_scd_keycloak

# Logs toate serviciile
docker stack ps scd
```

### Oprire Stack
```bash
docker stack rm scd
```

## 🗺️ Roadmap

### ✅ Implementat
- [x] RBAC complet pe toate endpoint-urile
- [x] Model de date complet pentru orar
- [x] Seed automat pentru date demo
- [x] Generator de orar (MVP)
- [x] Endpoint-uri pentru catalog (read + CRUD complet)
- [x] Endpoint `/timetables/me` cu restricție pentru studenți
- [x] Endpoint pentru editare manuală a intrărilor din orar (`PATCH /timetables/entries/{id}`)
- [x] Notificări (endpoint-uri + trigger la generare/publish)
- [x] Compatibilitate cu frontend-ul existent (alias-uri pentru endpoint-uri vechi)
- [x] **RabbitMQ** - Broker de mesaje pentru procesare asincronă
- [x] **Scheduling Engine Service** - Worker scalabil orizontal pentru generare asincronă
- [x] **Job tracking** - Urmărire status job-uri de generare (`GET /timetables/jobs/{id}`)
- [x] **AuditLog** - Logare acțiuni importante pentru audit
- [x] Teste automate în `demos/` pentru toate funcționalitățile

### 🚧 În Dezvoltare
- [ ] Îmbunătățire algoritm de generare orare (optimizare, constraint satisfaction, preferințe profesori)

### 📋 Planificat
- [ ] Upgrade distribuit: RabbitMQ + `scheduling-engine-service` (worker replicabil)
- [ ] Job status tracking pentru generare asincronă
- [ ] Unit tests (pytest)
- [ ] Migrații Alembic pentru schema DB
- [ ] Documentație API completă (OpenAPI/Swagger)

## 📄 Licență

Proiect academic pentru cursul de Sisteme Distribuite.

## 👥 Contribuitori

- Radu Roibu

---

**Notă**: Acest proiect este în dezvoltare activă. Pentru întrebări sau probleme, deschide un issue în repository.
