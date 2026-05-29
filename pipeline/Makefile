.PHONY: up down build logs migrate shell clean gpu-up

# Start all services (CPU mode)
up:
	docker compose up -d

# Start with GPU support
gpu-up:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Stop all services
down:
	docker compose down

# Rebuild all images
build:
	docker compose build

# Rebuild a single service
build-%:
	docker compose build $*

# View logs (all services)
logs:
	docker compose logs -f

# View logs for a specific service
logs-%:
	docker compose logs -f $*

# Run database migrations
migrate:
	docker compose exec backend flask db upgrade

# Create a new migration
migration:
	docker compose exec backend flask db migrate -m "$(msg)"

# Open a shell in a service
shell-%:
	docker compose exec $* /bin/sh

# Seed the database with demo data
seed:
	docker compose exec backend python -m seeds.demo

# Remove all data (volumes)
clean:
	docker compose down -v

# Check service health
status:
	docker compose ps

# Copy .env.example to .env if it doesn't exist
env:
	@test -f .env || cp .env.example .env && echo "Created .env from .env.example"
