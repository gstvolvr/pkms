"""Configuration management for PKMS."""
import os
from pathlib import Path
from typing import Optional

# Default configuration
HOME_PATH = os.path.expanduser('~')
DEFAULT_VAULT_NAME = 'vida'
DEFAULT_VAULT_PATH = f'{HOME_PATH}/obsidian/{DEFAULT_VAULT_NAME}'
DEFAULT_PHOTOS_PATH = f'{HOME_PATH}/photos'

class Config:
    """Configuration for PKMS operations."""

    def __init__(
        self,
        vault_path: Optional[str] = None,
        photos_path: Optional[str] = None,
    ):
        self.vault_path = Path(vault_path or os.getenv('PKMS_VAULT_PATH', DEFAULT_VAULT_PATH))
        self.photos_path = Path(photos_path or os.getenv('PKMS_PHOTOS_PATH', DEFAULT_PHOTOS_PATH))

    @property
    def pensieve_path(self) -> Path:
        """Path to daily notes (pensieve/day)."""
        return self.vault_path / 'pensieve' / 'day'

    @property
    def people_path(self) -> Path:
        """Path to people notes."""
        return self.vault_path / 'people'

    @property
    def locations_path(self) -> Path:
        """Path to location notes."""
        return self.vault_path / 'locations'

    @property
    def entities_paths(self) -> list[Path]:
        """List of entity paths (people, locations)."""
        return [self.people_path, self.locations_path]

    @property
    def concepts_path(self) -> Path:
        """Path to concepts notes."""
        return self.vault_path / 'concepts'

    @property
    def summaries_path(self) -> Path:
        """Path to summaries."""
        return self.vault_path / 'summaries'

    @property
    def embeddings_file(self) -> Path:
        """Path to embeddings file for RAG."""
        return self.vault_path / 'embeddings.json'

    def validate(self) -> bool:
        """Validate that required paths exist."""
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {self.vault_path}")
        if not self.pensieve_path.exists():
            raise ValueError(f"Pensieve path does not exist: {self.pensieve_path}")
        return True


# Global config instance (can be overridden)
_config: Optional[Config] = None

def get_config() -> Config:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config

def set_config(config: Config) -> None:
    """Set the global config instance."""
    global _config
    _config = config
