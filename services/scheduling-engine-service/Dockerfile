FROM python:3.11-slim

WORKDIR /app

# Copy requirements (from services/scheduling-engine-service/)
COPY services/scheduling-engine-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (from services/scheduling-engine-service/app/)
COPY services/scheduling-engine-service/app/ /app/app/

# Copy necessary code from timetable-management-service directly into app/
# This duplicates code but avoids import path issues
COPY services/timetable-management-service/app/models.py /app/app/shared_models.py
COPY services/timetable-management-service/app/db.py /app/app/shared_db.py
COPY services/timetable-management-service/app/services/timetable_generator.py /app/app/shared_timetable_generator.py
COPY services/timetable-management-service/app/services/notifications.py /app/app/shared_notifications.py
COPY services/timetable-management-service/app/services/audit.py /app/app/shared_audit.py

# Set shared code path and PYTHONPATH
# app module is at /app/shared/app/, so we need /app/shared in PYTHONPATH
ENV SHARED_CODE_PATH=/app/shared
ENV PYTHONPATH=/app/shared

# Run worker directly (not as module) to avoid path conflicts
# PYTHONPATH is set via ENV, and we also add it in main.py
CMD ["python", "/app/app/main.py"]
