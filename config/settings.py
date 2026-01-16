# config/settings.py
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file
except ImportError:
    # python-dotenv not installed, environment variables will still work
    pass


class Settings:
    """Settings manager for ReasonLoop - loads everything from .env file"""

    # Minimal defaults only for critical settings
    _defaults = {
        # Essential fallbacks
        "LLM_PROVIDER": "xai",
        "LLM_TEMPERATURE": 0.7,
        "LLM_MAX_TOKENS": 4096,
        "MAX_RETRIES": 3,
        "RETRY_DELAY": 2,
        # Rate limiting settings
        "RATE_LIMIT_ENABLED": True,
        "MAX_CONCURRENT_REQUESTS": 1,
        "RATE_LIMIT_DELAY": 2.0,
        "RATE_LIMIT_BACKOFF": 1.5,
    }

    def __init__(self):
        """Initialize settings from environment variables (.env file)"""
        self._settings = {}
        self._settings_file = Path("config/settings.json")

        # Load minimal defaults first
        self._settings.update(self._defaults)

        # Load everything from environment variables (.env file is already loaded)
        self._load_all_from_env()

        # Load settings from file if it exists (for backward compatibility)
        if self._settings_file.exists():
            self._load_from_file()

    def _load_all_from_env(self) -> None:
        """Load ALL settings from environment variables"""

        # LLM Provider settings
        self._load_env_var("LLM_PROVIDER")
        self._load_env_var("LLM_TEMPERATURE", float)
        self._load_env_var("LLM_MAX_TOKENS", int)
        self._load_env_var("MAX_RETRIES", int)
        self._load_env_var("RETRY_DELAY", float)

        # Rate limiting settings
        self._load_env_var("RATE_LIMIT_ENABLED", bool)
        self._load_env_var("MAX_CONCURRENT_REQUESTS", int)
        self._load_env_var("RATE_LIMIT_DELAY", float)
        self._load_env_var("RATE_LIMIT_BACKOFF", float)

        # XAI settings
        self._load_env_var("XAI_API_KEY")
        self._load_env_var("XAI_MODEL")
        self._load_env_var("XAI_API_URL")
        self._load_env_var("XAI_MODEL_ORCHESTRATOR")
        self._load_env_var("XAI_MODEL_PLANNER")
        self._load_env_var("XAI_MODEL_EXECUTOR")
        self._load_env_var("XAI_MODEL_REVIEWER")

        # Z.ai SDK settings
        self._load_env_var("ZAI_API_KEY")
        self._load_env_var("ZAI_MODEL")
        self._load_env_var("ZAI_BASE_URL")
        self._load_env_var("ZAI_TIMEOUT", float)
        self._load_env_var("ZAI_MAX_RETRIES", int)
        self._load_env_var("ZAI_MODEL_ORCHESTRATOR")
        self._load_env_var("ZAI_MODEL_PLANNER")
        self._load_env_var("ZAI_MODEL_EXECUTOR")
        self._load_env_var("ZAI_MODEL_REVIEWER")

        # Ollama settings
        self._load_env_var("OLLAMA_API_URL")
        self._load_env_var("OLLAMA_MODEL")
        self._load_env_var("OLLAMA_MODEL_ORCHESTRATOR")
        self._load_env_var("OLLAMA_MODEL_PLANNER")
        self._load_env_var("OLLAMA_MODEL_EXECUTOR")
        self._load_env_var("OLLAMA_MODEL_REVIEWER")

        # OpenAI settings
        self._load_env_var("OPENAI_API_KEY")
        self._load_env_var("OPENAI_MODEL")

        # Anthropic settings
        self._load_env_var("ANTHROPIC_API_KEY")
        self._load_env_var("ANTHROPIC_MODEL")
        self._load_env_var("ANTHROPIC_API_URL")

        # Database settings
        self._load_db_config()

        # Web search settings
        self._load_env_var("WEB_SEARCH_ENABLED", bool)
        self._load_env_var("WEB_SEARCH_RESULTS_COUNT", int)
        self._load_env_var("WEB-SEARCH-ENABLED", bool)  # Alternative naming
        self._load_env_var("WEB-SEARCH-RESULTS-COUNT", int)  # Alternative naming

        # Template settings
        self._load_env_var("PROMPT_TEMPLATE")
        self._load_env_var("DEFAULT_OBJECTIVE")

    def _load_env_var(self, key: str, var_type: type = str) -> None:
        """Load a single environment variable with type conversion"""
        env_value = os.getenv(key)
        if env_value is not None:
            try:
                if var_type == bool:
                    self._settings[key] = env_value.lower() in (
                        "true",
                        "1",
                        "yes",
                        "on",
                    )
                elif var_type == int:
                    self._settings[key] = int(env_value)
                elif var_type == float:
                    self._settings[key] = float(env_value)
                else:
                    self._settings[key] = env_value
            except ValueError as e:
                print(
                    f"Warning: Could not convert {key}={env_value} to {var_type.__name__}: {e}"
                )
                self._settings[key] = env_value  # Keep as string if conversion fails

    def _load_db_config(self) -> None:
        """Load database configuration from individual DB_ environment variables"""
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": self._convert_int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_DATABASE", "reasonloop"),
        }
        self._settings["DB_CONFIG"] = db_config

    def _convert_int(self, value: str) -> int:
        """Safely convert string to int"""
        try:
            return int(value)
        except ValueError:
            return 0

    def _load_from_file(self) -> None:
        """Load settings from JSON file (backward compatibility)"""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, "r") as f:
                    file_settings = json.load(f)
                    self._settings.update(file_settings)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading settings from file: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting by key"""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting by key"""
        self._settings[key] = value

    def save(self) -> Path:
        """Save settings to file"""
        # Create config directory if it doesn't exist
        self._settings_file.parent.mkdir(exist_ok=True)

        # Convert any non-serializable values to strings
        serializable_settings = {}
        for key, value in self._settings.items():
            if isinstance(value, (str, int, float, bool, list)) or value is None:
                serializable_settings[key] = value
            elif isinstance(value, dict):
                try:
                    json.dumps(value)
                    serializable_settings[key] = value
                except TypeError:
                    serializable_settings[key] = str(value)
            else:
                serializable_settings[key] = str(value)

        # Save to file
        with open(self._settings_file, "w") as f:
            json.dump(serializable_settings, f, indent=2)

        return self._settings_file

    def get_all(self) -> Dict[str, Any]:
        """Get all settings"""
        return self._settings.copy()


# Create a singleton instance
_settings = Settings()


# Public API
def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting by key"""
    return _settings.get(key, default)


def get_zai_model(role: str = None) -> str:
    """Get Z.ai model for a specific role (orchestrator, planner, executor, reviewer)"""
    if role:
        role_key = f"ZAI_MODEL_{role.upper()}"
        model = _settings.get(role_key)
        if model and model.strip():  # Check if not empty string
            return model

    # Fallback to default ZAI_MODEL
    return _settings.get("ZAI_MODEL", "glm-4.6")


def get_ollama_model(role: str = None) -> str:
    """Get Ollama model for a specific role (orchestrator, planner, executor, reviewer)"""
    if role:
        role_key = f"OLLAMA_MODEL_{role.upper()}"
        model = _settings.get(role_key)
        if model and model.strip():  # Check if not empty string
            return model

    # Fallback to default OLLAMA_MODEL
    return _settings.get("OLLAMA_MODEL", "llama3")


def get_model_for_provider(provider: str, role: str = None) -> str:
    """Get model for a specific provider and role"""
    if provider.lower() == "zai":
        return get_zai_model(role)
    elif provider.lower() == "ollama":
        return get_ollama_model(role)
    elif role:
        # For other providers, try role-specific first
        role_key = f"{provider.upper()}_MODEL_{role.upper()}"
        model = _settings.get(role_key)
        if model and model.strip():
            return model

    # Fallback to default model for provider
    provider_model_key = f"{provider.upper()}_MODEL"
    return _settings.get(provider_model_key, "grok-2-1212")


def update_setting(key: str, value: Any) -> None:
    """Update a setting by key"""
    _settings.set(key, value)


def save_settings() -> Path:
    """Save settings to file"""
    return _settings.save()


def get_all_settings() -> Dict[str, Any]:
    """Get all settings"""
    return _settings.get_all()
