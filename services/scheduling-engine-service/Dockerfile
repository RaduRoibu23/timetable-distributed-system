FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/

# Copy shared code from timetable-management-service
# Build context should be from project root, so we can access sibling services
COPY services/timetable-management-service/app/models.py /app/shared/models.py
COPY services/timetable-management-service/app/db.py /app/shared/db.py
COPY services/timetable-management-service/app/services/ /app/shared/services/
COPY services/timetable-management-service/app/core/ /app/shared/core/

# Create __init__.py for shared package
RUN touch /app/shared/__init__.py && \
    touch /app/shared/services/__init__.py && \
    touch /app/shared/core/__init__.py

# Set shared code path
ENV SHARED_CODE_PATH=/app/shared

# Run worker
CMD ["python", "-m", "app.main"]
