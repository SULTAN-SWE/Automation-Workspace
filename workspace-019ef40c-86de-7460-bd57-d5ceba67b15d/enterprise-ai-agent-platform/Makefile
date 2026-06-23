.PHONY: setup up down seed backend frontend import-workflows

setup:
	bash setup.sh

up:
	docker-compose up -d

down:
	docker-compose down

seed:
	curl -X POST http://localhost:8000/admin/seed

backend:
	cd fastapi && source .venv/bin/activate && uvicorn main:app --reload --port 8000

frontend:
	cd frontend && npm start

import-workflows:
	docker exec n8n mkdir -p /home/node/backup 2>/dev/null || true
	docker cp n8n/. n8n:/home/node/backup/
	docker exec n8n chmod -R 755 /home/node/backup
	docker exec n8n n8n import:workflow --input=/home/node/backup/
