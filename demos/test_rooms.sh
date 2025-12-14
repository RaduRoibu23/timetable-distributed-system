#!/bin/bash

BASE_URL="http://localhost:8000"

echo "Create room"
curl -X POST "$BASE_URL/rooms/" \
  -H "Content-Type: application/json" \
  -d '{"name": "A101", "capacity": 30}'
echo -e "\n"

echo "List rooms"
curl "$BASE_URL/rooms/"
echo -e "\n"

echo "Get room by id"
curl "$BASE_URL/rooms/1"
echo -e "\n"

echo "Update room"
curl -X PUT "$BASE_URL/rooms/1" \
  -H "Content-Type: application/json" \
  -d '{"name": "A101-updated", "capacity": 40}'
echo -e "\n"

echo "Delete room"
curl -X DELETE "$BASE_URL/rooms/1"
echo -e "\n"

echo "Get deleted room (should be 404)"
curl "$BASE_URL/rooms/1"
echo -e "\n"
