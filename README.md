# Customer Support Agent

Customer support agent for hands-on self-serve Opik workshop

## Quick Start

```bash
# One-command setup (installs deps + pre-commit hooks)
make setup

# Copy environment template and add your API keys
cp .env.example .env

# Run the app
make run
```

## Project Structure

```
├── app.py              # Application entrypoint
├── config.yml          # Model and project settings
├── src/
│   └── customer_support_agent/
│       └── utils/      # Config, logging, helpers
├── scripts/            # Python scripts, i.e. to simulate behavior unrelated to the core functionality of the app
├── notebooks/          # Jupyter notebooks
├── data/               # Data files (gitignored)
└── tests/              # Pytest tests
```

## Configuration

- **Secrets**: Set API keys in `.env` (see `.env.example`)
- **Settings**: Model parameters and project config in `config.yml`

```python
from customer_support_agent.utils.config import get_config

config = get_config()
config.validate()

print(config.model.name)        # claude-sonnet-4-5-20250514
print(config.anthropic_api_key) # from .env
```

## Development

Run `make help` to see all available commands:

| Command | Description |
|---------|-------------|
| `make setup` | Install dependencies and pre-commit hooks |
| `make run` | Run the application |
| `make test` | Run tests with pytest |
| `make lint` | Run linter (ruff check) |
| `make format` | Format code with ruff |
| `make typecheck` | Run type checker (mypy) |
| `make pre-commit` | Run all pre-commit hooks |
| `make clean` | Remove cache files |

## Versioning

Uses [Commitizen](https://commitizen-tools.github.io/commitizen/) for conventional commits. Bump version with:

```bash
poetry run cz bump
```
