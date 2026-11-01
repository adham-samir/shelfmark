# Shelfmark — common tasks. Run `make` or `make help` to list them.
COMPOSE := docker compose -f infra/compose.yaml

.PHONY: help up up-d down logs reset test api-test storefront-test gates

help:
	@echo "make up              Build and start the whole stack (foreground)"
	@echo "make up-d            Start the stack in the background"
	@echo "make down            Stop the stack"
	@echo "make logs            Follow the API and storefront logs"
	@echo "make reset           Delete the demo data and start fresh"
	@echo "make test            API tests + storefront typecheck/tests/build"
	@echo "make gates           Accessibility gate (needs the stack running)"

up:
	$(COMPOSE) up --build

up-d:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api storefront

reset:
	$(COMPOSE) down -v
	$(COMPOSE) up --build

test: api-test storefront-test

api-test:
	uv run --project services/api --extra test pytest services/api/tests -q

storefront-test:
	cd apps/storefront && npm ci && npm run typecheck && npm test && npm run build

gates:
	cd tests/accessibility && npm ci && \
		STOREFRONT_BASE_URL=http://127.0.0.1:3000 \
		SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 npm run check
