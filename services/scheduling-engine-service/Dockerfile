FROM python:3.12-slim

WORKDIR /app

# Install shared package first
COPY shared/ /app/shared/
RUN cd /app/shared && pip install --no-cache-dir -e .

# Copy requirements and install dependencies
COPY services/scheduling-engine-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/scheduling-engine-service/app/ /app/app/

# Run worker
CMD ["python", "/app/app/main.py"]
