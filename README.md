# Timetable Distributed System

A distributed system for managing school timetables, developed as a project for the Distributed Systems (SCD) course. The project implements a FastAPI backend with Keycloak authentication, role-based access control (RBAC), automatic timetable generation, and notifications.

## Architecture Overview

The system is orchestrated using **Docker Swarm** and implements a microservices architecture with the following components:

### Core Services

- **Keycloak** (port 8181) - Identity and Access Management (IAM) using OIDC protocol
- **PostgreSQL** - Database for Keycloak and application data
- **RabbitMQ** (ports 5672, 15672) - Message broker for asynchronous processing
- **Timetable Management Service** (port 8000) - FastAPI REST API for timetable management
- **Scheduling Engine Service** - Worker service for asynchronous timetable generation (horizontally scalable)
- **Notifications Service** - Worker service for processing notification events from RabbitMQ
- **Frontend** (port 3000) - React-based web interface

### Architecture Diagram

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│   Keycloak   │────▶│  PostgreSQL │
│  (Browser)  │     │  (Auth/OIDC) │     │   (Storage) │
└─────────────┘     └──────────────┘     └─────────────┘
      │                     │
      │                     │
      ▼                     ▼
┌─────────────┐     ┌──────────────────────┐
│  Frontend   │────▶│  Timetable Management│
│  (React)    │     │  Service (FastAPI)    │
└─────────────┘     └──────────────────────┘
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
                                            ├──────────────┐
                                            │             │
                                            ▼             ▼
                                     ┌──────────────┐  ┌──────────────┐
                                     │  Scheduling  │  │ Notifications│
                                     │  Engine      │  │   Service    │
                                     │  (Workers)   │  │   (Worker)   │
                                     └──────────────┘  └──────────────┘
                                            │             │
                                            └─────┬───────┘
                                                  │
                                                  ▼
                                           ┌─────────────┐
                                           │  PostgreSQL │
                                           │  (App Data) │
                                           └─────────────┘
```

### Service Communication Flow

1. **Authentication Flow**: Client authenticates with Keycloak, receives JWT token
2. **API Requests**: Frontend sends authenticated requests to Timetable Management Service
3. **Timetable Generation**: 
   - Management Service creates job and publishes to RabbitMQ queue `timetable_generation`
   - Scheduling Engine Service (one of 2 replicas) consumes job, generates timetable, publishes notification event
   - Notifications Service consumes notification event and sends notifications to users
4. **Data Persistence**: All services share the same PostgreSQL database

## Implemented Features

### Authentication and Authorization

- Keycloak integration with dedicated realm (`timetable-realm`)
- JWT token verification for all endpoints
- **RBAC (Role-Based Access Control)** implementation:
  - `student` - can only view their own class timetable
  - `professor` - can view timetables and send notifications
  - `secretariat` - can publish timetables and send notifications
  - `scheduler` - can generate/modify timetables
  - `admin` / `sysadmin` - full access to all operations

### Data Model

The system uses SQLAlchemy ORM with the following models:

- **SchoolClass** - School classes (e.g., IX-A, IX-B, X-A, X-B, XI-A)
- **Subject** - Subjects/curriculum subjects
- **TimeSlot** - Time slots (5 weekdays × 7 hours = 35 slots per week)
- **Curriculum** - Curriculum plan (hours per week per subject and class), includes `teacher_id` for teacher assignment
- **TimetableEntry** - Timetable entries (class + timeslot → subject + optional room), includes `version` for optimistic locking
- **UserProfile** - Mapping username → class (for students) or teacher_id (for professors)
- **Notification** - User notifications
- **Room** - Classrooms with capacity
- **TeacherAvailability** - Teacher availability for specific time slots
- **RoomAvailability** - Room availability for specific time slots
- **TimetableJob** - Tracks asynchronous timetable generation jobs
- **ConflictReport** - Reports conflicts encountered during timetable generation
- **AuditLog** - Logs important actions for audit purposes

Database constraints:
- `UNIQUE(class_id, timeslot_id)` on TimetableEntry to prevent overlaps
- `UNIQUE(teacher_id, weekday, index_in_day)` on TeacherAvailability
- `UNIQUE(room_id, weekday, index_in_day)` on RoomAvailability

### Automatic Data Seeding

On startup, the system automatically seeds demo data:
- 4 classes: `IX-A`, `IX-B`, `X-A`, `X-B`
- 35 time slots (Monday-Friday, hours 1-7)
- 13 subjects (Romanian, Mathematics, Computer Science, Physics, Chemistry, etc.)
- Complete curriculum (35 hours/week per class)
- 80 students (20 per class): `student01` to `student80`
- 10 professors: `professor01` to `professor10` with sequential `teacher_id`
- 7 rooms (6 regular rooms + 1 sports hall) with various capacities
- UserProfile mappings for all users

### API Endpoints

#### Authentication
- `GET /me` - Get current user information (username, roles, class_id, teacher_id)

#### Catalog Management (CRUD)
- `GET /classes` - List all classes
- `POST /classes` - Create class (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /classes/{id}` - Update class (RBAC: `secretariat`, `admin`, `sysadmin`)
- `DELETE /classes/{id}` - Delete class (RBAC: `secretariat`, `admin`, `sysadmin`)
- `GET /subjects` - List all subjects
- `POST /subjects` - Create subject (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /subjects/{id}` - Update subject (RBAC: `secretariat`, `admin`, `sysadmin`)
- `DELETE /subjects/{id}` - Delete subject (RBAC: `secretariat`, `admin`, `sysadmin`)
- `GET /curricula` - List all curricula
- `POST /curricula` - Create curriculum (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /curricula/{id}` - Update curriculum (RBAC: `secretariat`, `admin`, `sysadmin`)
- `DELETE /curricula/{id}` - Delete curriculum (RBAC: `secretariat`, `admin`, `sysadmin`)
- `GET /timeslots` - List all time slots (read-only)

#### Subject-Teacher Mapping
- `GET /subjects/{subject_id}/teachers` - List teachers assigned to a subject
- `POST /subjects/{subject_id}/teachers` - Assign teacher to subject for a class (RBAC: `secretariat`, `admin`, `sysadmin`)
- `DELETE /subjects/{subject_id}/teachers/{teacher_id}` - Remove teacher assignment (RBAC: `secretariat`, `admin`, `sysadmin`)

#### Availability Management
- `GET /teachers/{teacher_id}/availability` - List teacher availability
- `POST /teachers/{teacher_id}/availability` - Set teacher availability (RBAC: `professor`, `admin`, `sysadmin`)
- `PUT /teachers/{teacher_id}/availability/{id}` - Update teacher availability
- `DELETE /teachers/{teacher_id}/availability/{id}` - Delete teacher availability
- `GET /rooms/{room_id}/availability` - List room availability
- `POST /rooms/{room_id}/availability` - Set room availability (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /rooms/{room_id}/availability/{id}` - Update room availability
- `DELETE /rooms/{room_id}/availability/{id}` - Delete room availability

#### Timetables
- `POST /timetables/generate` - Generate timetable asynchronously for one or more classes (via RabbitMQ)
  - **RBAC**: `scheduler`, `secretariat`, `admin`, `sysadmin`
  - Body: `{"class_id": 1}` or `{"class_ids": [1, 2]}`
  - Returns: `{"job_ids": [1, 2], "message": "..."}`
  - Jobs are processed asynchronously by Scheduling Engine Service
- `GET /timetables/jobs/{job_id}` - Get status of a generation job
  - Returns: `{"id": 1, "status": "pending|processing|completed|failed", ...}`
- `GET /timetables/jobs/{job_id}/conflicts` - Get conflict reports for a job
- `GET /timetables/classes/{class_id}` - Get timetable for a class
- `GET /timetables/me` - Get current user's timetable
  - **Student**: automatically returns their class timetable (ignores parameters)
  - **Other roles**: can specify `?class_id=X`
- `GET /timetables/stats` - Get statistics about timetables (total generated, conflicts, distribution, room usage)
- `PATCH /timetables/entries/{id}` - Edit a timetable entry manually
  - **RBAC**: `secretariat`, `admin`, `sysadmin`
  - Body: `{"subject_id": 2, "room_id": 3, "version": 1}` (version required for optimistic locking)
  - Validates: teacher availability, room availability, room capacity, overlaps

#### Notifications
- `POST /notifications/send` - Send notification to user or class (RBAC: `secretariat`, `admin`, `sysadmin`, `professor`)
- `GET /notifications/me` - List current user's notifications
- `PATCH /notifications/{id}/read` - Mark notification as read

#### Audit Logs
- `GET /audit-logs` - List audit logs with filtering and pagination (RBAC: `admin`, `sysadmin`)
  - Query parameters: `username`, `action`, `resource_type`, `limit`, `offset`

#### Rooms
- `GET /rooms` - List all rooms
- `POST /rooms` - Create room (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /rooms/{id}` - Update room (RBAC: `secretariat`, `admin`, `sysadmin`)
- `DELETE /rooms/{id}` - Delete room (RBAC: `secretariat`, `admin`, `sysadmin`)

#### Lessons (Legacy - for compatibility)
- `GET /lessons` - List lessons
- `POST /lessons` - Create lesson (RBAC: `secretariat`, `admin`, `sysadmin`)
- `PUT /lessons/{id}` - Update lesson
- `DELETE /lessons/{id}` - Delete lesson

#### Frontend Compatibility (Aliases)
- `POST /schedule/run` - Alias for `POST /timetables/generate`
- `GET /lessons/mine` - Alias for `GET /timetables/me`
- `GET /users` - Returns `[]` (compatibility)

### Timetable Generation Algorithm

The system implements an enhanced timetable generation algorithm that:

1. **Respects Curriculum**: Ensures each class has exactly 35 hours per week as specified in curriculum
2. **Teacher Availability**: Checks teacher availability before assigning subjects
3. **Room Availability**: Checks room availability and capacity before assignment
4. **Preference for Early Hours**: Prefers hours 1-5, avoids late hours 6-7
5. **Uniform Distribution**: Distributes subjects evenly across days (max 2 same subject per day)
6. **Conflict Detection**: Reports conflicts (teacher unavailable, room unavailable, room capacity issues)
7. **Room Assignment**: Automatically assigns available rooms with sufficient capacity

**Asynchronous Processing**:
- Jobs are published to RabbitMQ queue `timetable_generation`
- Scheduling Engine Service (2 replicas) processes jobs in parallel (horizontal scaling)
- Status tracking for each job via `TimetableJob` model
- Automatic notifications sent after generation via Notifications Service

### Notifications System

The system implements a separate Notifications Service that:

1. **Consumes Events from RabbitMQ**: Listens to `notifications` queue
2. **Processes Event Types**:
   - `timetable_generated` - When a timetable is generated
   - `timetable_entry_modified` - When a timetable entry is modified
   - `teacher_unavailable` - When teacher availability issues occur
   - `room_unavailable` - When room availability issues occur
   - `notification_custom` - Generic custom notifications
3. **Sends Notifications**: Creates notification records in database for users/classes
4. **Manual Notifications**: Endpoint `POST /notifications/send` remains in Management Service for manual notifications

### Optimistic Locking

Timetable entries include a `version` field to prevent concurrent modification conflicts:
- Each entry has a `version` number (starts at 1)
- When updating, client must provide current `version`
- If version mismatch → HTTP 409 Conflict
- On successful update, version is incremented

### Advanced Validations

The system performs comprehensive validations:

1. **Teacher Overlap**: Prevents same teacher from having multiple lessons at same time
2. **Room Overlap**: Prevents same room from being used by multiple classes simultaneously
3. **Room Capacity**: Ensures room capacity is sufficient for class size
4. **Teacher Availability**: Checks teacher availability before assignment
5. **Room Availability**: Checks room availability before assignment

## Quick Start

### Prerequisites

- Docker Engine with Swarm support
- Docker Desktop (on Windows) or Docker Engine on Linux
- WSL2 (recommended on Windows)
- Git (to clone repository)

### Deployment Steps

1. **Initialize Docker Swarm** (if not already active):
```bash
docker swarm init
```

2. **Build Docker Images**:
```bash
bash build-images.sh
```

This builds:
- `roiburadu/timetable-management-service:dev1`
- `roiburadu/scheduling-engine-service:dev1`
- `roiburadu/notifications-service:dev1`

**Note**: Frontend image (`roiburadu/timetable-frontend:dev`) must be built manually:
```bash
docker build -t roiburadu/timetable-frontend:dev -f services/frontend/Dockerfile services/frontend
```

3. **Deploy Stack**:
```bash
docker stack deploy -c docker-stack.yml scd
```

4. **Wait for Services to Start**:
```bash
docker stack services scd
```

Wait until all services reach `1/1` (Running) state. This may take 30-60 seconds for Keycloak to fully initialize.

5. **Seed Keycloak Users** (optional, if you need demo users):
```bash
# Wait for Keycloak to be ready, then:
bash demos/seed_keycloak.sh
```

This creates:
- 80 students (student01-student80)
- 10 professors (professor01-professor10)
- 3 admins, 2 secretariat, 3 schedulers, 1 sysadmin

6. **Access Services**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Keycloak Admin: http://localhost:8181 (admin/admin)
- RabbitMQ Management: http://localhost:15672 (admin/admin)

### First Time Setup

After deployment, the system automatically:
- Creates database tables
- Seeds demo data (4 classes, 80 students, 10 professors, 7 rooms)
- Imports Keycloak realm configuration

You only need to run `seed_keycloak.sh` if you want to create Keycloak users (students, professors, admins, etc.).

### Default Credentials

All demo users have password identical to username:
- `sysadmin` / `sysadmin` (super administrator)
- `admin01` / `admin01` (administrator)
- `professor01` / `professor01` (professor)
- `student01` / `student01` (student)
- `secretariat01` / `secretariat01` (secretariat)
- `scheduler01` / `scheduler01` (scheduler)

Keycloak Admin Console:
- Username: `admin`
- Password: `admin`

### Demo Users

All users have password identical to username:

| Username | Role | Description |
|----------|------|-------------|
| `student01` - `student80` | student | Students (20 per class, 4 classes) |
| `professor01` - `professor10` | professor | Professors with teacher_id 1-10 |
| `secretariat01`, `secretariat02` | secretariat | Secretariat staff |
| `scheduler01`, `scheduler02`, `scheduler03` | scheduler | Timetable schedulers |
| `admin01`, `admin02`, `admin03` | admin | Administrators |
| `sysadmin` | sysadmin | Super administrator |

## Testing

The project includes test scripts in the `demos/` directory:

### Test RBAC
Verifies that students receive 403 for privileged operations:
```bash
bash demos/test_rbac.sh
```

### Test Seed
Verifies that demo data was created correctly:
```bash
bash demos/test_seed.sh
```

### Test Timetable (Student Access)
Verifies that students can only see their own class timetable:
```bash
bash demos/test_timetable_me.sh
```

### Test Authentication
Tests token retrieval and `/me` endpoint:
```bash
bash demos/test_auth.sh
```

### Test New Features
Comprehensive test for all new backend features:
```bash
bash demos/test_all_new_features.sh
```

Individual feature tests:
- `test_availability.sh` - Teacher and room availability
- `test_subject_teacher_mapping.sh` - Subject-teacher mapping
- `test_optimistic_locking.sh` - Optimistic locking
- `test_audit_logs.sh` - Audit logs endpoint
- `test_timetable_stats.sh` - Timetable statistics
- `test_conflict_reports.sh` - Conflict reports
- `test_advanced_validations.sh` - Advanced validations

## Project Structure

```
timetable-distributed-system/
├── docker-stack.yml              # Docker Swarm configuration
├── build-images.sh               # Script to build Docker images
├── keycloak/
│   └── realms/
│       └── timetable-realm.json  # Keycloak realm configuration (auto-imported)
├── shared/
│   └── timetable_shared/        # Shared Python package
│       ├── models.py             # SQLAlchemy models
│       ├── db.py                # Database setup
│       └── services/
│           ├── timetable_generator.py
│           ├── notifications.py
│           ├── audit.py
│           └── rabbitmq_client.py
│       └── setup.py             # Package setup
├── services/
│   ├── timetable-management-service/
│   │   ├── app/
│   │   │   ├── api/              # FastAPI endpoints
│   │   │   │   ├── routes_auth.py
│   │   │   │   ├── routes_rooms.py
│   │   │   │   ├── routes_lessons.py
│   │   │   │   ├── routes_catalog_read.py
│   │   │   │   ├── routes_timetables.py
│   │   │   │   ├── routes_notifications.py
│   │   │   │   ├── routes_availability.py
│   │   │   │   ├── routes_audit.py
│   │   │   │   └── routes_compat.py
│   │   │   ├── core/             # Configuration and security
│   │   │   │   ├── config.py
│   │   │   │   ├── security.py
│   │   │   │   └── rbac.py       # RBAC dependency
│   │   │   ├── services/         # Business logic
│   │   │   │   ├── timetable_generator.py (re-exports from shared)
│   │   │   │   ├── notifications.py (re-exports from shared)
│   │   │   │   ├── rabbitmq_client.py (re-exports from shared)
│   │   │   │   └── audit.py
│   │   │   ├── models.py         # SQLAlchemy models (re-exports from shared)
│   │   │   ├── db.py             # Database configuration
│   │   │   ├── init_db.py        # Automatic seeding
│   │   │   └── main.py           # FastAPI entry point
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── scheduling-engine-service/
│   │   ├── app/
│   │   │   └── main.py           # Worker for asynchronous generation
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── notifications-service/
│   │   ├── app/
│   │   │   └── main.py           # Worker for processing notification events
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── frontend/                 # React frontend
│       ├── src/
│       │   ├── components/
│       │   ├── services/
│       │   ├── constants/
│       │   └── utils/
│       ├── package.json
│       ├── vite.config.js
│       ├── nginx.conf
│       └── Dockerfile
├── demos/                        # Test scripts
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
│   ├── test_availability.sh
│   ├── test_subject_teacher_mapping.sh
│   ├── test_optimistic_locking.sh
│   ├── test_audit_logs.sh
│   ├── test_timetable_stats.sh
│   ├── test_conflict_reports.sh
│   ├── test_advanced_validations.sh
│   ├── test_all_new_features.sh
│   ├── seed_keycloak.sh
│   └── find_user.sh
└── README.md
```

## Role-Based Permissions

| Action | student | professor | secretariat | scheduler | admin | sysadmin |
|--------|---------|-----------|-------------|-----------|-------|----------|
| View own class timetable | Yes | Yes | Yes | Yes | Yes | Yes |
| View other classes timetables | No | Yes | Yes | Yes | Yes | Yes |
| Generate timetable | No | No | Yes | Yes | Yes | Yes |
| Modify timetable | No | No | Yes | Yes | Yes | Yes |
| Publish timetable | No | No | Yes | No | Yes | Yes |
| Send notifications | No | Yes | Yes | No | Yes | Yes |
| CRUD Rooms/Lessons | No | No | Yes | No | Yes | Yes |
| CRUD Catalog | No | No | Yes | No | Yes | Yes |
| Manage availability | No | Own only | Yes | No | Yes | Yes |
| View audit logs | No | No | No | No | Yes | Yes |
| View statistics | Yes | Yes | Yes | Yes | Yes | Yes |

## API Usage Examples

### Get Token
```bash
curl -X POST "http://localhost:8181/realms/timetable-realm/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=timetable-backend" \
  -d "grant_type=password" \
  -d "username=sysadmin01" \
  -d "password=sysadmin01"
```

### Generate Timetable (as sysadmin)
```bash
TOKEN="<your-token>"
curl -X POST "http://localhost:8000/timetables/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"class_id": 1}'
```

### View My Timetable (as student)
```bash
TOKEN="<student-token>"
curl "http://localhost:8000/timetables/me" \
  -H "Authorization: Bearer $TOKEN"
```

### Update Timetable Entry (with optimistic locking)
```bash
TOKEN="<admin-token>"
curl -X PATCH "http://localhost:8000/timetables/entries/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"room_id": 2, "version": 1}'
```

## Development

### Build Images

To build Docker images for custom services:
```bash
bash build-images.sh
```

This builds:
- `roiburadu/timetable-management-service:dev1`
- `roiburadu/scheduling-engine-service:dev1`
- `roiburadu/notifications-service:dev1`

**Note**: Frontend image (`roiburadu/timetable-frontend:dev`) must be built manually:
```bash
cd services/frontend
docker build -t roiburadu/timetable-frontend:dev .
```

### Rebuild Services (after code changes)

1. **Rebuild Images**:
```bash
# Backend services
bash build-images.sh

# Frontend (if changed)
docker build -t roiburadu/timetable-frontend:dev -f services/frontend/Dockerfile services/frontend
```

2. **Update Services**:
```bash
# Backend
docker service update --force scd_timetable_backend

# Frontend
docker service update --force scd_timetable_frontend

# Scheduling Engine
docker service update --force scd_scheduling_engine

# Notifications Service
docker service update --force scd_notifications_service
```

**Note**: Services will automatically restart with new images. No data loss occurs as data is persisted in PostgreSQL volumes.

### View Logs

```bash
# Backend logs
docker service logs -f scd_timetable_backend

# Scheduling Engine logs
docker service logs -f scd_scheduling_engine

# Notifications Service logs
docker service logs -f scd_notifications_service

# Keycloak logs
docker service logs -f scd_scd_keycloak

# All services status
docker stack ps scd
```

### Stop Stack

```bash
docker stack rm scd
```

**Note**: This stops all services but does NOT delete data. PostgreSQL data is persisted in Docker volumes. To completely reset:
1. Stop stack: `docker stack rm scd`
2. Remove volumes: `docker volume rm scd_postgres_data`
3. Redeploy: `docker stack deploy -c docker-stack.yml scd`

## Service Replication and Scaling

### Timetable Management Service
- **Replicas**: 1
- **Reason**: Stateless API service, can be scaled if needed
- **Communication**: Direct database access, publishes to RabbitMQ

### Scheduling Engine Service
- **Replicas**: 2
- **Reason**: Horizontal scaling for parallel timetable generation
- **Communication**: Consumes from RabbitMQ queue `timetable_generation`
- **Load Distribution**: RabbitMQ distributes jobs across replicas

### Notifications Service
- **Replicas**: 1
- **Reason**: Can be scaled if notification volume increases
- **Communication**: Consumes from RabbitMQ queue `notifications`

### RabbitMQ Usage

RabbitMQ is used for:
1. **Timetable Generation Queue** (`timetable_generation`):
   - Published by: Timetable Management Service
   - Consumed by: Scheduling Engine Service (2 replicas)
   - Message format: `{"job_id": 1, "class_id": 1}`

2. **Notifications Queue** (`notifications`):
   - Published by: Scheduling Engine Service, Timetable Management Service
   - Consumed by: Notifications Service
   - Message format: `{"event_type": "timetable_generated", "event_data": {...}}`

## Concurrency Handling

### Optimistic Locking

Timetable entries use optimistic locking to prevent concurrent modification conflicts:
- Each entry has a `version` field (starts at 1)
- Client must provide current `version` when updating
- If version mismatch → HTTP 409 Conflict
- On successful update, version is incremented

### Conflict Prevention

The system validates:
- Teacher overlaps (same teacher cannot have multiple lessons simultaneously)
- Room overlaps (same room cannot be used by multiple classes simultaneously)
- Room capacity (ensures sufficient capacity for class size)
- Teacher availability (checks availability before assignment)
- Room availability (checks availability before assignment)

## Implementation Status

### Completed Features

- [x] Complete RBAC on all endpoints
- [x] Complete data model for timetables
- [x] Automatic seeding for demo data (4 classes, 80 students, 10 professors, 7 rooms)
- [x] Enhanced timetable generator (considers availability, preferences, conflicts)
- [x] Complete catalog endpoints (read + CRUD)
- [x] Endpoint `/timetables/me` with restriction for students
- [x] Endpoint for manual timetable entry editing (`PATCH /timetables/entries/{id}`)
- [x] Notifications (endpoints + automatic triggers via Notifications Service)
- [x] Compatibility with existing frontend (aliases for old endpoints)
- [x] **RabbitMQ** - Message broker for asynchronous processing
- [x] **Scheduling Engine Service** - Horizontally scalable worker for asynchronous generation
- [x] **Notifications Service** - Separate microservice for processing notification events
- [x] **Job tracking** - Status tracking for generation jobs (`GET /timetables/jobs/{id}`)
- [x] **Conflict Reports** - Reports conflicts during generation (`GET /timetables/jobs/{id}/conflicts`)
- [x] **AuditLog** - Logging important actions for audit
- [x] **Teacher/Room Availability** - CRUD endpoints for managing availability
- [x] **Subject-Teacher Mapping** - Assign teachers to subjects
- [x] **Optimistic Locking** - Version-based concurrency control
- [x] **Advanced Validations** - Comprehensive overlap and capacity checks
- [x] **Timetable Statistics** - Statistics endpoint for reporting
- [x] **Keycloak Integration** - User name display from Keycloak, proper authentication flow
- [x] **Frontend Improvements** - Room selection dropdown, edit validation, error handling

### Known Issues

- Edit button error (resolved - validation added)
- Professor editing (minor UI improvements needed)

## License

Academic project for the Distributed Systems course.

## Contributors

- Radu Roibu

---

**Note**: This project is under active development. For questions or issues, please open an issue in the repository.
