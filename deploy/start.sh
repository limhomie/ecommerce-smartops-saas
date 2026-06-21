#!/bin/bash
set -e
echo "=== E-Commerce SmartOps Agent ==="
echo "Building and starting services..."
docker compose up -d --build
echo ""
echo "Waiting for services to be ready..."
sleep 3
docker compose ps
echo ""
echo "Frontend : http://localhost"
echo "API      : http://localhost/api/health"
