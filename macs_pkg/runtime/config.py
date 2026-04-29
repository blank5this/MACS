"""Configuration management for MACS."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path

from ..collaboration.base import CollaborationConfig as BaseCollaborationConfig


class ConfigSource(Enum):
    """Configuration source priority."""
    DEFAULT = 0
    ENV = 1
    FILE = 2
    CODE = 3  # Highest priority


@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    name: str
    role: str
    model: str = "gpt-4"
    system_prompt: Optional[str] = None
    max_retries: int = 3
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MACSConfig:
    """Main configuration class for MACS."""
    # Runtime settings
    runtime_name: str = "macs"
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Agent defaults
    default_model: str = "gpt-4"
    default_timeout: Optional[float] = 60.0

    # Collaboration
    collaboration: BaseCollaborationConfig = field(default_factory=BaseCollaborationConfig)

    # Agents
    agents: List[AgentConfig] = field(default_factory=list)

    # Tools
    enable_tools: bool = True
    tool_timeout: float = 30.0

    # Context
    context_max_size: int = 1000
    enable_context_persistence: bool = False

    # Monitoring
    enable_monitoring: bool = True
    monitoring_interval: float = 60.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        import dataclasses
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MACSConfig":
        """Create config from dictionary."""
        import dataclasses

        # Handle nested config
        if "collaboration" in data:
            collab_data = data["collaboration"]
            if isinstance(collab_data, dict):
                collaboration = BaseCollaborationConfig(**collab_data)
            else:
                collaboration = collab_data
            data["collaboration"] = collaboration

        agents = []
        for agent_data in data.get("agents", []):
            agents.append(AgentConfig(**agent_data))
        data["agents"] = agents

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ConfigManager:
    """Manages configuration from multiple sources.

    Priority (highest to lowest):
    1. Code (programmatic)
    2. Environment variables
    3. Config file
    4. Defaults
    """

    ENV_PREFIX = "MACS_"

    def __init__(self, config_file: Optional[str] = None):
        self._config_file = config_file
        self._config = MACSConfig()
        self._sources: Dict[str, ConfigSource] = {}

        # Load in priority order
        self._load_defaults()
        if config_file:
            self._load_from_file(config_file)
        self._load_from_env()

    def _load_defaults(self) -> None:
        """Load default configuration."""
        self._config = MACSConfig()
        self._mark_all_sources(ConfigSource.DEFAULT)

    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from file."""
        path = Path(config_file)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        import json
        with open(path) as f:
            data = json.load(f)

        self._apply_config(data)
        self._mark_all_sources(ConfigSource.FILE)

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            "MACS_LOG_LEVEL": ("log_level", str),
            "MACS_DEFAULT_MODEL": ("default_model", str),
            "MACS_DEFAULT_MODE": ("collaboration.default_mode", str),
            "MACS_ENABLE_TOOLS": ("enable_tools", lambda x: x.lower() == "true"),
            "MACS_TIMEOUT": ("default_timeout", float),
        }

        for env_var, (config_path, converter) in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                self._set_nested(config_path, converter(value))
                self._sources[config_path] = ConfigSource.ENV

    def _apply_config(self, data: Dict[str, Any]) -> None:
        """Apply configuration data."""
        self._config = MACSConfig.from_dict(data)

    def _mark_all_sources(self, source: ConfigSource) -> None:
        """Mark all config fields as coming from a source."""
        import dataclasses
        for f in dataclasses.fields(self._config):
            self._sources[f.name] = source

    def _set_nested(self, path: str, value: Any) -> None:
        """Set a nested configuration value."""
        parts = path.split(".")
        current = self._config

        for part in parts[:-1]:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                return

        if hasattr(current, parts[-1]):
            setattr(current, parts[-1], value)

    def _get_nested(self, path: str, default: Any = None) -> Any:
        """Get a nested configuration value."""
        parts = path.split(".")
        current = self._config

        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                return default

        return current

    def get(self, path: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            path: Dot-separated path (e.g., "collaboration.default_mode").
            default: Default value if not found.

        Returns:
            Configuration value or default.
        """
        return self._get_nested(path, default)

    def set(self, path: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            path: Dot-separated path.
            value: Value to set.
        """
        self._set_nested(path, value)
        self._sources[path] = ConfigSource.CODE

    def get_config(self) -> MACSConfig:
        """Get the full configuration object."""
        return self._config

    def get_source(self, path: str) -> ConfigSource:
        """Get the source of a configuration value.

        Args:
            path: Configuration path.

        Returns:
            Source of the value.
        """
        return self._sources.get(path, ConfigSource.DEFAULT)

    def save_to_file(self, config_file: str) -> None:
        """Save current configuration to file.

        Args:
            config_file: Path to save to.
        """
        import json
        with open(config_file, "w") as f:
            json.dump(self._config.to_dict(), f, indent=2)


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """Get the global config manager.

    Args:
        config_file: Optional config file to load.

    Returns:
        ConfigManager instance.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager


def load_config(config_file: str) -> MACSConfig:
    """Load configuration from a file.

    Args:
        config_file: Path to config file.

    Returns:
        MACSConfig instance.
    """
    manager = ConfigManager(config_file)
    return manager.get_config()
