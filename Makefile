.PHONY: help install up down restart logs shell db-shell migrate backtest paper live test clean

help:
	@echo "Volatility Harvester - Make Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install      Install Python dependencies"
	@echo "  make up           Start all services (Docker)"
	@echo "  make down         Stop all services"
	@echo "  make restart      Restart all services"
	@echo ""
	@echo "Database:"
	@echo "  make migrate      Run database migrations"
	@echo "  make db-shell     Open PostgreSQL shell"
	@echo ""
	@echo "Trading:"
	@echo "  make backtest     Run backtest"
	@echo "  make paper        Start paper trading"
	@echo "  make live         Start live trading (REAL MONEY!)"
	@echo ""
	@echo "Development:"
	@echo "  make logs         View application logs"
	@echo "  make shell        Open app container shell"
	@echo "  make test         Run tests"
	@echo "  make clean        Clean up containers and volumes"
	@echo ""

install:
	pip install -r requirements.txt

up:
	docker-compose up -d
	@echo "Services started!"
	@echo "API: http://localhost:8000"
	@echo "Metrics: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@echo "Prometheus: http://localhost:9091"

down:
	docker-compose down

restart:
	docker-compose restart app

logs:
	docker-compose logs -f app

shell:
	docker-compose exec app /bin/bash

db-shell:
	docker-compose exec postgres psql -U volharvester -d volharvester

migrate:
	docker-compose exec app alembic upgrade head

migrate-create:
	@read -p "Enter migration name: " name; \
	docker-compose exec app alembic revision --autogenerate -m "$$name"

backtest:
	@echo "Running backtest..."
	@curl -X POST http://localhost:8000/backtest \
		-H "Content-Type: application/json" \
		-d '{"start_date": "2023-01-01T00:00:00", "end_date": "2023-12-31T23:59:59", "initial_capital": 10000}'

paper:
	@echo "Starting paper trading..."
	@curl -X POST http://localhost:8000/start \
		-H "Content-Type: application/json" \
		-d '{"mode": "paper", "initial_capital": 10000}'

paper-stop:
	@echo "Stopping paper trading..."
	@curl -X POST http://localhost:8000/stop

live:
	@echo "WARNING: This will start LIVE trading with REAL MONEY!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	@curl -X POST http://localhost:8000/start \
		-H "Content-Type: application/json" \
		-d '{"mode": "live"}'

live-stop:
	@echo "Stopping live trading..."
	@curl -X POST http://localhost:8000/stop

live-flatten:
	@echo "EMERGENCY FLATTEN - Selling all positions at market!"
	@curl -X POST http://localhost:8000/emergency-flatten

status:
	@curl -s http://localhost:8000/status | python -m json.tool

config:
	@curl -s http://localhost:8000/config | python -m json.tool

test:
	pytest app/tests -v --cov=app --cov-report=html

test-unit:
	pytest app/tests/unit -v

test-integration:
	pytest app/tests/integration -v

clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov .pytest_cache .coverage

dev:
	uvicorn app.api.server:app --reload --host 0.0.0.0 --port 8000

format:
	black app/
	isort app/

lint:
	flake8 app/
	mypy app/
