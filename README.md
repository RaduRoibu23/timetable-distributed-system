# Timetable Distributed System

## Authentication Test (Keycloak + FastAPI)
To test the authentication flow:

1. Start Keycloak on port 8181
2. Start the timetable-management-service
3. Run:
   ./test_auth.sh
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000