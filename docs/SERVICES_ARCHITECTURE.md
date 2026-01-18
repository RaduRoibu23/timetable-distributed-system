# Services Architecture Documentation

This document explains all services in the Timetable Distributed System, how they work, why they are connected, and how they communicate.

## Overview

The system is a microservices architecture orchestrated with Docker Swarm. All services share the same PostgreSQL database and communicate through:
- **Direct HTTP/REST API calls** (synchronous)
- **RabbitMQ message queues** (asynchronous)
- **Shared database** (PostgreSQL)

## Service Components

### 1. PostgreSQL Database (`scd_postgres`)

**Purpose**: Centralized data storage for all services

**What it stores**:
- Application data: classes, subjects, timetables, users, notifications, audit logs
- Keycloak data: users, realms, clients, sessions

**Why shared**: 
- Single source of truth for all data
- Ensures consistency across services
- Simplifies data relationships (foreign keys work across services)

**Connections**:
- All services connect to the same PostgreSQL instance
- Uses connection pooling for performance

**Configuration**:
- Database: `keycloak`
- User: `keycloak`
- Password: `keycloak`
- Port: `5432` (internal Docker network)

---

### 2. Keycloak (`scd_keycloak`)

**Purpose**: Identity and Access Management (IAM) - handles authentication and authorization

**What it does**:
- Manages user accounts (students, professors, admins, etc.)
- Issues JWT tokens for authentication
- Defines roles (student, professor, secretariat, scheduler, admin, sysadmin)
- Provides OIDC protocol for secure authentication

**Why it's needed**:
- Centralized authentication (single sign-on)
- Industry-standard security (OIDC/OAuth2)
- Role-based access control (RBAC) foundation
- User management without custom implementation

**How it connects**:
- **To PostgreSQL**: Stores user data, sessions, realm configuration
- **To Frontend**: Frontend authenticates users via Keycloak login page
- **To Backend**: Backend verifies JWT tokens from Keycloak on every API request

**Communication Flow**:
1. User logs in via Frontend → Keycloak
2. Keycloak validates credentials → returns JWT token
3. Frontend stores token → sends with every API request
4. Backend verifies token with Keycloak → grants/denies access

**Configuration**:
- Admin: `admin` / `admin`
- Realm: `timetable-realm`
- Port: `8181` (external), `8080` (internal)

---

### 3. RabbitMQ (`rabbitmq`)

**Purpose**: Message broker for asynchronous communication between services

**What it does**:
- Provides message queues for decoupled service communication
- Enables horizontal scaling (multiple workers can process jobs)
- Ensures message persistence (messages survive service restarts)

**Why it's needed**:
- **Decoupling**: Services don't need to know about each other directly
- **Scalability**: Can add more workers without changing code
- **Reliability**: Messages are persisted and retried on failure
- **Performance**: Long-running tasks (timetable generation) don't block API

**Queues**:
1. **`timetable_generation`**: Jobs for generating timetables
2. **`notifications`**: Events that trigger notifications

**How it connects**:
- **From Timetable Management Service**: Publishes generation jobs
- **To Scheduling Engine Service**: Consumes generation jobs
- **From Scheduling Engine Service**: Publishes notification events
- **To Notifications Service**: Consumes notification events

**Configuration**:
- User: `admin` / `admin`
- AMQP Port: `5672`
- Management UI: `15672`

---

### 4. Timetable Management Service (`timetable_backend`)

**Purpose**: Main REST API service - handles all HTTP requests from frontend

**What it does**:
- Exposes REST API endpoints for timetable management
- Validates requests and enforces RBAC
- Manages CRUD operations for classes, subjects, rooms, timetables
- Creates generation jobs and publishes them to RabbitMQ
- Handles manual timetable editing with optimistic locking

**Why it's separate**:
- Stateless API service (can be scaled horizontally)
- Clear separation of concerns (API vs. background processing)
- Easy to add more API endpoints without affecting workers

**How it connects**:
- **To PostgreSQL**: Reads/writes all application data
- **To Keycloak**: Verifies JWT tokens, fetches user info
- **To RabbitMQ**: Publishes generation jobs and notification events
- **From Frontend**: Receives HTTP requests

**Key Responsibilities**:
- Authentication/authorization (via Keycloak)
- Request validation
- Business logic (conflict detection, availability checks)
- Job creation and tracking
- Manual timetable editing

**Configuration**:
- Port: `8000`
- Database: Shared PostgreSQL
- Keycloak: Internal URL for token verification

---

### 5. Scheduling Engine Service (`scheduling_engine`)

**Purpose**: Worker service that generates timetables asynchronously

**What it does**:
- Consumes timetable generation jobs from RabbitMQ
- Runs the timetable generation algorithm
- Saves generated timetables to database
- Publishes notification events when generation completes

**Why it's separate**:
- **Performance**: Timetable generation is CPU-intensive and can take time
- **Scalability**: Can run multiple replicas (2 by default) to process jobs in parallel
- **Reliability**: If one worker fails, others continue processing
- **Non-blocking**: API doesn't wait for generation to complete

**How it connects**:
- **From RabbitMQ**: Consumes `timetable_generation` queue
- **To PostgreSQL**: Reads curriculum/availability data, writes generated timetables
- **To RabbitMQ**: Publishes notification events after generation

**Scaling**:
- Default: 2 replicas
- RabbitMQ distributes jobs across replicas (round-robin)
- Each replica processes one job at a time (QoS prefetch_count=1)

**Workflow**:
1. Receives job message: `{"job_id": 1, "class_id": 1}`
2. Updates job status to "processing"
3. Generates timetable using algorithm
4. Saves entries to database
5. Updates job status to "completed"
6. Publishes notification event

---

### 6. Notifications Service (`notifications_service`)

**Purpose**: Worker service that processes notification events and creates user notifications

**What it does**:
- Consumes notification events from RabbitMQ
- Creates notification records in database for users/classes
- Handles different event types (timetable_generated, timetable_updated, etc.)

**Why it's separate**:
- **Decoupling**: Notification logic is isolated from main API
- **Scalability**: Can scale independently if notification volume increases
- **Reliability**: Notifications are processed asynchronously, don't block main operations

**How it connects**:
- **From RabbitMQ**: Consumes `notifications` queue
- **To PostgreSQL**: Creates notification records

**Event Types Handled**:
- `timetable_generated`: Notifies class when timetable is generated
- `timetable_updated`: Notifies class when timetable is modified
- `timetable_entry_modified`: Notifies class of specific entry changes
- `teacher_unavailable`: Notifies class of teacher availability issues
- `room_unavailable`: Notifies class of room availability issues
- `notification_custom`: Generic custom notifications

**Workflow**:
1. Receives event: `{"event_type": "timetable_generated", "event_data": {...}}`
2. Processes event based on type
3. Creates notification records for target users/classes
4. Commits to database

---

### 7. Frontend (`timetable_frontend`)

**Purpose**: React-based web interface for users

**What it does**:
- Provides user interface for viewing/editing timetables
- Handles authentication flow with Keycloak
- Displays data from backend API
- Implements role-based UI (different views for students vs. admins)

**Why it's separate**:
- **Technology**: React/JavaScript vs. Python backend
- **Deployment**: Can be served via CDN, different scaling needs
- **Development**: Frontend and backend can be developed independently

**How it connects**:
- **To Keycloak**: User login, token refresh
- **To Timetable Management Service**: All API calls (GET, POST, PATCH, DELETE)
- **No direct connection** to database, RabbitMQ, or worker services

**Communication Flow**:
1. User logs in → Frontend redirects to Keycloak
2. Keycloak returns token → Frontend stores it
3. User makes action → Frontend calls Backend API with token
4. Backend verifies token → Returns data
5. Frontend displays data → User sees result

---

## Service Communication Patterns

### Synchronous Communication (HTTP/REST)

**Used for**:
- Frontend → Backend API calls
- Backend → Keycloak token verification
- Backend → Keycloak user info fetching

**Characteristics**:
- Request-response pattern
- Immediate feedback
- Blocking (waits for response)

### Asynchronous Communication (RabbitMQ)

**Used for**:
- Backend → Scheduling Engine (generation jobs)
- Scheduling Engine → Notifications Service (notification events)

**Characteristics**:
- Fire-and-forget pattern
- Non-blocking
- Retry on failure
- Horizontal scaling support

### Shared Database (PostgreSQL)

**Used for**:
- All services read/write application data
- Keycloak stores authentication data
- Job tracking, notifications, audit logs

**Characteristics**:
- Single source of truth
- ACID transactions
- Foreign key relationships work across services

---

## Data Flow Examples

### Example 1: Generate Timetable

```
1. User (admin) clicks "Generate Timetable" in Frontend
2. Frontend → Backend: POST /timetables/generate {class_id: 1}
3. Backend:
   - Creates TimetableJob record (status: "pending")
   - Publishes to RabbitMQ: {"job_id": 1, "class_id": 1}
   - Returns immediately: {"job_ids": [1]}
4. Frontend shows "Job created, processing..."
5. Scheduling Engine (Worker 1) consumes message
6. Worker 1:
   - Updates job status to "processing"
   - Generates timetable (reads curriculum, availability from DB)
   - Saves TimetableEntry records to DB
   - Updates job status to "completed"
   - Publishes to RabbitMQ: {"event_type": "timetable_generated", ...}
7. Notifications Service consumes event
8. Notifications Service creates Notification records for class students
9. Students see notifications when they refresh frontend
```

### Example 2: Edit Timetable Entry

```
1. User (secretariat) edits a timetable entry in Frontend
2. Frontend → Backend: PATCH /timetables/entries/123 {room_id: 5, version: 2}
3. Backend:
   - Verifies JWT token with Keycloak
   - Checks RBAC (secretariat allowed)
   - Validates optimistic locking (version matches)
   - Validates teacher/room availability
   - Updates TimetableEntry in DB
   - Publishes notification event to RabbitMQ
4. Notifications Service processes event
5. Notifications Service creates notifications for affected class
6. Frontend shows success message
```

### Example 3: User Login

```
1. User enters credentials in Frontend
2. Frontend → Keycloak: POST /realms/timetable-realm/protocol/openid-connect/token
3. Keycloak:
   - Validates credentials (checks PostgreSQL)
   - Generates JWT token with user roles
   - Returns token to Frontend
4. Frontend stores token
5. Frontend → Backend: GET /me (with token)
6. Backend:
   - Verifies token signature with Keycloak
   - Extracts username and roles from token
   - Queries UserProfile from PostgreSQL
   - Returns user info (class_id, teacher_id, etc.)
7. Frontend displays user-specific view
```

---

## Why This Architecture?

### Microservices Benefits

1. **Separation of Concerns**: Each service has a single responsibility
2. **Independent Scaling**: Can scale workers without scaling API
3. **Technology Diversity**: Frontend (React) vs. Backend (Python) vs. IAM (Keycloak)
4. **Fault Isolation**: If one service fails, others continue working
5. **Development Speed**: Teams can work on different services independently

### Why RabbitMQ?

1. **Decoupling**: Services don't need to know about each other
2. **Reliability**: Messages are persisted, retried on failure
3. **Scalability**: Easy to add more workers
4. **Performance**: Long operations don't block API

### Why Shared Database?

1. **Consistency**: Single source of truth
2. **Relationships**: Foreign keys work across services
3. **Simplicity**: No need for complex data synchronization
4. **Transactions**: ACID guarantees for critical operations

### Why Keycloak?

1. **Security**: Industry-standard authentication
2. **User Management**: Built-in user management UI
3. **Standards**: OIDC/OAuth2 compliance
4. **RBAC**: Role-based access control out of the box

---

## Service Dependencies

```
Frontend
  └─> Keycloak (authentication)
  └─> Timetable Management Service (all API calls)

Timetable Management Service
  └─> PostgreSQL (data storage)
  └─> Keycloak (token verification, user info)
  └─> RabbitMQ (publish jobs/events)

Scheduling Engine Service
  └─> RabbitMQ (consume jobs)
  └─> PostgreSQL (read curriculum, write timetables)
  └─> RabbitMQ (publish notification events)

Notifications Service
  └─> RabbitMQ (consume events)
  └─> PostgreSQL (create notifications)

Keycloak
  └─> PostgreSQL (user data, sessions)

All Services
  └─> PostgreSQL (shared database)
```

---

## Scaling Considerations

### Horizontal Scaling

- **Scheduling Engine**: Can scale to N replicas (currently 2)
  - RabbitMQ distributes jobs automatically
  - Each replica processes one job at a time
  
- **Timetable Management Service**: Can scale to N replicas (currently 1)
  - Stateless API, any replica can handle any request
  - Load balancer needed for multiple replicas

- **Notifications Service**: Can scale to N replicas (currently 1)
  - RabbitMQ distributes events automatically

### Vertical Scaling

- **PostgreSQL**: Can increase resources for more concurrent connections
- **RabbitMQ**: Can increase resources for higher message throughput

---

## Deployment

All services are deployed using Docker Swarm:

```bash
docker stack deploy -c docker-stack.yml scd
```

Services are defined in `docker-stack.yml` with:
- Image names
- Environment variables
- Network configuration
- Volume mounts
- Replica counts
- Restart policies

---

## Monitoring and Debugging

### View Service Logs

```bash
# Backend API
docker service logs -f scd_timetable_backend

# Scheduling Engine
docker service logs -f scd_scheduling_engine

# Notifications Service
docker service logs -f scd_notifications_service

# Keycloak
docker service logs -f scd_scd_keycloak
```

### Check Service Status

```bash
docker stack services scd
docker stack ps scd
```

### RabbitMQ Management

Access http://localhost:15672 (admin/admin) to:
- View queue status
- Monitor message rates
- Inspect messages
- Check connections

---

## Summary

The system uses a microservices architecture where:
- **Frontend** handles user interface
- **Timetable Management Service** handles API requests
- **Scheduling Engine Service** processes generation jobs asynchronously
- **Notifications Service** processes notification events asynchronously
- **Keycloak** handles authentication
- **RabbitMQ** enables asynchronous communication
- **PostgreSQL** stores all data

Services communicate through HTTP (synchronous) and RabbitMQ (asynchronous), with all services sharing the same PostgreSQL database for data consistency.
