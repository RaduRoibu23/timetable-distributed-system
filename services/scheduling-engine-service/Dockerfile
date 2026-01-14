FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/

# Copy shared code from timetable-management-service (models, services)
# This will be mounted at runtime, but we need the structure
RUN mkdir -p /app/shared

# Run worker
CMD ["python", "-m", "app.main"]
