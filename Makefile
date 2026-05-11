# NGTI — top-level Makefile.
#
# The `demo` target brings a clean clone to a running demo in one command.
# Other targets are conveniences for common dev flows.

.PHONY: demo dev down clean seed migrate contracts test health

# ─── Demo flow ────────────────────────────────────────────────────────────────

demo: ## Bring up the full stack from a clean clone, seed, and start dev servers
	docker compose -f infra/docker-compose.yml up -d postgres redis
	uv run --directory apps/api alembic upgrade head
	uv run --directory apps/api python -m apps.api.seeds.demo --fresh
	pnpm install --frozen-lockfile || pnpm install
	pnpm contracts:gen:local
	pnpm dev

# ─── Lifecycle ────────────────────────────────────────────────────────────────

dev: ## Start api + web dev servers (assumes postgres + redis already up)
	pnpm dev

down: ## Stop docker containers (keeps the volume)
	docker compose -f infra/docker-compose.yml down

clean: ## Stop and wipe the postgres volume (destroys local data)
	docker compose -f infra/docker-compose.yml down -v

# ─── Data ─────────────────────────────────────────────────────────────────────

migrate: ## Apply Alembic migrations
	uv run --directory apps/api alembic upgrade head

seed: ## Reseed demo data (drops generated rows, keeps fixtures)
	uv run --directory apps/api python -m apps.api.seeds.demo --fresh

# ─── Build / verify ───────────────────────────────────────────────────────────

contracts: ## Regenerate TypeScript contracts from FastAPI OpenAPI
	pnpm contracts:gen:local

test: ## Run all tests (both stacks)
	uv run --directory apps/api pytest
	pnpm --filter web run test

health: ## Full health check: lint + typecheck + tests on both stacks
	pnpm health
