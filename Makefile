.PHONY: help test test-backend test-frontend lint build-frontend up down logs

help:
	@echo "Comandos disponibles:"
	@echo "  make test           Ejecuta pytest y Vitest"
	@echo "  make test-backend   Ejecuta la suite del backend"
	@echo "  make test-frontend  Ejecuta la suite del frontend"
	@echo "  make lint           Revisa formato y lint del backend"
	@echo "  make build-frontend Compila el frontend con Vite"
	@echo "  make up             Levanta db, backend, frontend y pgadmin"
	@echo "  make down           Detiene los contenedores sin borrar volúmenes"
	@echo "  make logs           Sigue los logs de todos los servicios"

test: test-backend test-frontend

test-backend:
	cd backend && MUSIC_PROVIDER=simulated python -m pytest

test-frontend:
	cd frontend && npm run test

lint:
	cd backend && ruff format --check . && ruff check .

build-frontend:
	cd frontend && npm run build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f
