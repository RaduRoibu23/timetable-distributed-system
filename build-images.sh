#!/usr/bin/env bash
# Build Docker images for the timetable distributed system

set -e

echo "Building timetable-management-service..."
cd services/timetable-management-service
docker build -t roiburadu/timetable-management-service:dev1 .
cd ../..

echo "Building scheduling-engine-service..."
# Build from project root to access shared package
docker build -f services/scheduling-engine-service/Dockerfile -t roiburadu/scheduling-engine-service:dev1 .

echo "Building notifications-service..."
# Build from project root to access shared package
docker build -f services/notifications-service/Dockerfile -t roiburadu/notifications-service:dev1 .

echo "All images built successfully!"
echo ""
echo "Images:"
echo "  - roiburadu/timetable-management-service:dev1"
echo "  - roiburadu/scheduling-engine-service:dev1"
echo "  - roiburadu/notifications-service:dev1"
