.PHONY: up down logs backend-shell worker-shell test test-backend test-frontend lint fmt backup restore

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend-shell:
	docker compose exec api bash

worker-shell:
	docker compose exec worker bash

test-backend:
	docker compose exec api pytest

test-frontend:
	docker compose exec web npm run test

test: test-backend test-frontend

lint:
	docker compose exec api ruff check app
	docker compose exec web npm run lint

fmt:
	docker compose exec api ruff format app
	docker compose exec web npm run format

# One-command backup/restore (NFR-20). Dumps to ./backups/<timestamp>/.
backup:
	mkdir -p backups/$$(date +%Y%m%d-%H%M%S)
	docker compose exec -T mongo mongodump --archive --db=finance_tracker \
		> backups/$$(date +%Y%m%d-%H%M%S)/finance_tracker.archive

restore:
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=backups/<ts>/finance_tracker.archive" && exit 1)
	docker compose exec -T mongo mongorestore --archive --nsInclude='finance_tracker.*' --drop < $(FILE)
