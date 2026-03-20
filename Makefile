.PHONY: setup create-db build-vector-db setup-databases run test lint format typecheck test-prompts clean help

.DEFAULT_GOAL := help

# ============================================================================
# SETUP
# ============================================================================

setup: ## Install dependencies and set up pre-commit hooks
	@echo "🔧 Setting up project..."
	@if command -v pyenv > /dev/null 2>&1; then \
		if pyenv versions --bare | grep -q "^3\.12"; then \
			echo "✓ Python 3.12 already installed, skipping pyenv install"; \
		else \
			echo "📦 Installing Python 3.12 via pyenv (this may take a while)..."; \
			pyenv install 3.12 || true; \
		fi; \
		pyenv local 3.12 || echo "⚠️  Could not set pyenv local, continuing..."; \
	else \
		echo "⚠️  pyenv not found, skipping Python installation"; \
	fi
	@echo "📦 Configuring Poetry..."
	@poetry config virtualenvs.in-project true
	@echo "📦 Installing dependencies (this may take 5-10 minutes)..."
	@poetry install --with=dev
	@echo "🔄 Updating dependencies..."
	@poetry update
	@echo "🔧 Installing pre-commit hooks..."
	@poetry run pre-commit install
	@echo "✓ Setup complete. Copy .env.example to .env and add your API keys."

# ============================================================================
# DATABASE SETUP
# ============================================================================

create-db: ## Create SQLite database from JSON data files
	@echo "🔨 Creating SQLite database..."
	@poetry run python scripts/create_db.py

build-vector-db: ## Build ChromaDB vector database from FAQ text
	@echo "🚀 Building ChromaDB vector database..."
	@poetry run python scripts/build_vector_db.py

setup-databases: create-db build-vector-db ## Create both SQLite and ChromaDB databases

# ============================================================================
# DEVELOPMENT
# ============================================================================

run: ## Run the application
	poetry run streamlit run app.py

test: ## Run tests with pytest
	poetry run pytest ./tests -v

lint: ## Run linter (ruff check)
	poetry run ruff check .

format: ## Format code with ruff
	poetry run ruff format .
	poetry run ruff check --fix .

typecheck: ## Run type checker (mypy)
	poetry run mypy src/

pre-commit: ## Run all pre-commit hooks
	poetry run pre-commit run --all-files

# ============================================================================
# UTILITIES
# ============================================================================

requirements: ## Export requirements.txt for deployment
	poetry export -f requirements.txt --output requirements.txt --without-hashes

clean: ## Remove cache files and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleaned up cache files"

# ============================================================================
# HELP
# ============================================================================

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
