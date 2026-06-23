#!/usr/bin/env bash
# One-command setup for the Enterprise AI Agent Platform.
# Run this on your local machine (not inside a container).
set -e

cd "$(dirname "$0")"

echo "Loading environment variables from .env..."
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo "ERROR: .env file not found. Copy .env.example to .env and configure it first."
  exit 1
fi

echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "ERROR: docker-compose is required but not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: Python 3 is required but not installed."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "ERROR: Node.js is required but not installed."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "ERROR: npm is required but not installed."; exit 1; }

# Trap Ctrl+C to stop background services and containers
cleanup() {
  echo ""
  echo "Stopping background services and containers..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  docker-compose down
  exit 0
}
trap cleanup SIGINT SIGTERM

echo "Starting infrastructure (n8n + SQL Server)..."
docker-compose up -d

echo "Waiting for n8n to be healthy..."
for i in {1..60}; do
  if curl -s http://localhost:5678/healthz >/dev/null 2>&1; then
    echo "n8n is up."
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "WARNING: n8n did not become healthy in 2 minutes. Continuing anyway..."
  fi
  sleep 2
done

echo "Installing FastAPI backend dependencies..."
cd fastapi
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
cd ..

echo "Starting FastAPI backend..."
cd fastapi
source .venv/bin/activate
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

echo "Waiting for backend to start..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "Backend is up."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "WARNING: Backend did not become healthy in 60 seconds. Continuing anyway..."
  fi
  sleep 2
done

echo "Seeding demo data..."
curl -s -X POST http://localhost:8000/admin/seed || echo "WARNING: Seed request failed."

echo "Importing n8n workflows..."
docker exec n8n mkdir -p /home/node/backup 2>/dev/null || true
docker cp n8n/. n8n:/home/node/backup/
docker exec n8n chmod -R 755 /home/node/backup
# The CLI import runs as root inside the container; workflows are placed under the n8n user directory.
docker exec n8n n8n import:workflow --input=/home/node/backup/ || {
  echo "WARNING: Could not import workflows automatically. Import them manually from the n8n UI (Settings > Workflows > Import from File)."
}

echo "Installing React frontend dependencies..."
cd frontend
npm install

echo "Starting React frontend..."
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================================"
echo " Platform is starting up!"
echo "========================================================"
echo "n8n UI:        http://localhost:5678"
echo "Backend API:   http://localhost:8000"
echo "React Frontend: http://localhost:3000"
echo ""
echo "Next manual steps:"
echo "1. Open http://localhost:5678 and log in (admin / change-me-n8n-password)."
echo "2. Create an OpenAI credential named 'OpenAI API' in n8n."
echo "3. Activate the imported workflows."
echo "4. Open http://localhost:3000, log in with any email, and start chatting."
echo ""
echo "Press Ctrl+C to stop all services."
echo "========================================================"
wait
