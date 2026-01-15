FROM python:3.12-slim

WORKDIR /app

# Copy shared package
COPY shared/timetable_shared/ /app/timetable_shared/
COPY shared/setup.py /app/setup.py

# Install shared package
RUN pip install --no-cache-dir -e /app/

# Copy and install service dependencies
COPY services/notifications-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY services/notifications-service/app/ /app/app/

# Run worker
CMD ["python", "-u", "/app/app/main.py"]
