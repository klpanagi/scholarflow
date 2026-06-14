.PHONY: help build up down logs clean dev backend frontend

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build all containers
	docker compose build

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## View logs
	docker compose logs -f

clean: ## Remove all containers, volumes, and data
	docker compose down -v

dev: ## Start development environment
	docker compose up -d postgres redis elasticsearch minio tika grobid
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend: ## Start backend only
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Start frontend only
	cd frontend && npm run dev

install: ## Install all dependencies
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

test: ## Run tests
	cd backend && pytest
	cd frontend && npm run lint

migrate: ## Run database migrations
	cd backend && alembic upgrade head

migration: ## Create new migration
	cd backend && alembic revision --autogenerate -m "$(msg)"

db-reset: ## Reset database
	docker compose down -v postgres
	docker compose up -d postgres
	sleep 3
	$(MAKE) migrate
