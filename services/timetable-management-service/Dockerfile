FROM python:3.12-slim

WORKDIR /app

# Copy shared package
COPY shared/timetable_shared/ /app/timetable_shared/
COPY shared/setup.py /app/setup.py

# Install shared package
RUN pip install --no-cache-dir -e /app/

# Copy and install service dependencies
COPY services/timetable-management-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY services/timetable-management-service/app/ /app/app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
