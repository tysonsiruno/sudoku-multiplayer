# Makefile for common development tasks
# BUG #556-565 FIX: Development automation

.PHONY: help install dev test lint format clean docker-build docker-up docker-down migrate backup

# Default target
help:
	@echo "Minesweeper Multiplayer - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install dependencies"
	@echo "  make dev           - Run development server"
	@echo ""
	@echo "Quality:"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo "  make security      - Run security checks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  - Build Docker images"
	@echo "  make docker-up     - Start all services"
	@echo "  make docker-down   - Stop all services"
	@echo "  make docker-logs   - View logs"
	@echo ""
	@echo "Database:"
	@echo "  make migrate       - Run database migrations"
	@echo "  make backup        - Backup database"
	@echo "  make restore       - Restore database"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-prod   - Deploy to production"
	@echo "  make clean         - Clean temporary files"

# Setup
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt || true

dev:
	cd server && python app.py

# Quality
test:
	pytest --cov=server --cov-report=term-missing

lint:
	flake8 server
	pylint server
	black --check server

format:
	black server
	isort server

security:
	safety check
	bandit -r server

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Services started. Access app at http://localhost:5000"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f app

docker-clean:
	docker-compose down -v
	docker system prune -f

# Database
migrate:
	@echo "Running database migrations..."
	psql $(DATABASE_URL) < server/migrations/001_security_and_performance.sql

migrate-docker:
	docker-compose exec db psql -U minesweeper -d minesweeper -f /docker-entrypoint-initdb.d/001_security_and_performance.sql

backup:
	@echo "Backing up database..."
	mkdir -p backups
	pg_dump $(DATABASE_URL) > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup complete"

restore:
	@echo "Restoring database from backup..."
	@echo "Available backups:"
	@ls -1 backups/*.sql
	@read -p "Enter backup filename: " backup; \
	psql $(DATABASE_URL) < backups/$$backup

# Deployment
deploy-prod:
	@echo "Deploying to production..."
	git push origin main
	@echo "Deployment triggered. Check CI/CD pipeline for status."

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/
	@echo "Cleanup complete"

# Quick development setup
quick-start: install docker-up
	@echo "Development environment ready!"
	@echo "App: http://localhost:5000"
	@echo "Database: localhost:5432"
	@echo "Redis: localhost:6379"
