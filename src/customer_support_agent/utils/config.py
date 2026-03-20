"""
Unified configuration loader for Customer Support Agent
Loads secrets from .env and settings from config.yml
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv


class ConfigDict(dict):
    """Dict with dot notation access for cleaner syntax."""

    def __getattr__(self, key: str) -> Any:
        try:
            value = self[key]
            if isinstance(value, dict):
                return ConfigDict(value)
            return value
        except KeyError:
            raise AttributeError(f"Config has no key '{key}'")

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


class Config:
    """
    Configuration container.

    Secrets loaded from .env, settings from config.yml.
    Access YAML values via dot notation: config.model.temperature
    """

    def __init__(self, yaml_config: dict, env_vars: dict):
        self._config = ConfigDict(yaml_config)
        self._env = env_vars

    # Secrets (from .env)
    @property
    def opik_api_key(self) -> str:
        return self._env.get("OPIK_API_KEY", "")

    @property
    def anthropic_api_key(self) -> str:
        return self._env.get("ANTHROPIC_API_KEY", "")

    @property
    def openai_api_key(self) -> str:
        return self._env.get("OPENAI_API_KEY", "")

    @property
    def opik_workspace(self) -> str:
        return self._env.get("OPIK_WORKSPACE", "")

    @property
    def opik_project_name(self) -> str:
        return self._env.get("OPIK_PROJECT_NAME", "Customer Support Agent")

    # Settings (from config.yml) - dynamic access
    @property
    def model(self) -> ConfigDict:
        return ConfigDict(self._config.get("model", {}))

    @property
    def project(self) -> ConfigDict:
        return ConfigDict(self._config.get("project", {}))

    def __getattr__(self, key: str) -> Any:
        """Allow access to any top-level YAML key."""
        if key.startswith("_"):
            raise AttributeError(key)
        return self._config.get(key, ConfigDict({}))

    @classmethod
    def load(cls, config_path: str = "config.yml", env_path: str = ".env") -> "Config":
        """Load configuration from .env and config.yml"""
        load_dotenv(dotenv_path=env_path)

        yaml_config: dict[str, Any] = {}
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                yaml_config = yaml.safe_load(f) or {}

        return cls(yaml_config, dict(os.environ))

    def validate(self) -> None:
        """Validate required secrets are present."""
        errors = []

        if not self.opik_api_key:
            errors.append("Missing OPIK_API_KEY in .env")
        # Check for either OpenAI or Anthropic API key
        if not self.openai_api_key and not self.anthropic_api_key:
            errors.append("Missing OPENAI_API_KEY or ANTHROPIC_API_KEY in .env")

        if errors:
            raise ValueError("Configuration errors:\n  - " + "\n  - ".join(errors))


# Singleton instance
_settings: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _settings
    if _settings is None:
        _settings = Config.load()
    return _settings
