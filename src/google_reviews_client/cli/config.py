import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_GLOBS = ("google-reviews-config.*.json",)

_EMAIL_INDEX = 2
_PROJECT_INDEX = 1
_MIN_PARTS_FOR_EMAIL = 3
_MIN_PARTS_FOR_PROJECT = 2


@dataclass
class Config:
    """Represents a loaded config file with credentials and targets."""

    path: Path
    credentials_data: dict
    targets: list[dict] = field(default_factory=list)

    @property
    def email(self) -> str | None:
        """Extract email from filename (google-reviews-config.{project}.{email}.json)."""
        stem = self.path.stem
        parts = stem.split(".", 2)
        return parts[_EMAIL_INDEX] if len(parts) >= _MIN_PARTS_FOR_EMAIL else None

    @property
    def project_number(self) -> str | None:
        """Extract project number from filename."""
        stem = self.path.stem
        parts = stem.split(".", 2)
        return parts[_PROJECT_INDEX] if len(parts) >= _MIN_PARTS_FOR_PROJECT else None


def find_config_files(cwd: Path, explicit_path: Path | None = None) -> list[Path]:
    """Find config files in cwd. Returns list (may be empty)."""
    if explicit_path is not None:
        if not explicit_path.is_file():
            msg = f"Config file not found: {explicit_path}"
            raise FileNotFoundError(msg)
        logger.info("Using specified config: %s", explicit_path)
        return [explicit_path]

    matches: list[Path] = []
    for pattern in CONFIG_GLOBS:
        logger.debug("Searching for %s in %s", pattern, cwd)
        matches.extend(cwd.glob(pattern))

    if matches:
        for path in sorted(matches):
            logger.info("Found config: %s", path.name)
    else:
        logger.debug("No config files found")

    return sorted(matches)


def load_config(path: Path) -> Config:
    """Load a config file and return a Config object."""
    data = json.loads(path.read_text())
    return Config(
        path=path,
        credentials_data=data.get("credentials", {}),
        targets=data.get("targets", []),
    )


def save_config(config: Config) -> None:
    """Save a Config object to its file path."""
    data = {
        "credentials": config.credentials_data,
        "targets": config.targets,
    }
    config.path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    logger.info("Config saved to %s", config.path.name)


def build_config_path(cwd: Path, project_number: str, email: str) -> Path:
    """Build the config file path from project number and email."""
    return cwd / f"google-reviews-config.{project_number}.{email.lower()}.json"
