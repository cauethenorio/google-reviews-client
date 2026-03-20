import errno
import json
import logging
import urllib.parse
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from google_reviews_client.constants import SCOPES

logger = logging.getLogger(__name__)

TOKENS_GLOBS = ("credentials.*.json",)
CLIENT_SECRETS_GLOBS = ("client_secret*.json", "*_client_secret*.json")
LOCALHOST_HOSTS = frozenset(("localhost", "127.0.0.1", "::1"))


class MultipleFilesFoundError(Exception):
    def __init__(self, files_found: list[Path]):
        self.files_found = files_found
        super().__init__(f"Multiple files found: {files_found}")


class NoFilesFoundError(Exception):
    pass


class PortsAlreadyInUseError(Exception):
    def __init__(self, failed_ports: list[int]):
        self.failed_ports = failed_ports
        super().__init__(f"All ports in use: {failed_ports}")


def _find_files(cwd: Path, globs: tuple[str, ...], explicit_path: Path | None = None) -> Path:
    """Find exactly one file matching globs, or use explicit path.

    Returns the single matching Path.
    Raises FileNotFoundError, NoFilesFoundError, or MultipleFilesFoundError.
    """
    if explicit_path is not None:
        if not explicit_path.is_file():
            msg = f"File not found: {explicit_path}"
            raise FileNotFoundError(msg)
        logger.info("Using specified file: %s", explicit_path)
        return explicit_path

    matches: list[Path] = []
    for pattern in globs:
        logger.debug("Searching for %s in %s", pattern, cwd)
        matches.extend(cwd.glob(pattern))

    if len(matches) == 1:
        logger.info("Found %s", matches[0].name)
        return matches[0]

    if len(matches) == 0:
        raise NoFilesFoundError()

    raise MultipleFilesFoundError(files_found=sorted(matches))


def find_tokens_files(cwd: Path, explicit_path: Path | None = None) -> Path:
    """Find a tokens file (credentials.*.json)."""
    return _find_files(cwd, TOKENS_GLOBS, explicit_path)


def find_client_secrets_files(cwd: Path, explicit_path: Path | None = None) -> Path:
    """Find a client secrets file (client_secret*.json)."""
    return _find_files(cwd, CLIENT_SECRETS_GLOBS, explicit_path)


def load_tokens(path: Path) -> Credentials:
    """Load credentials from a tokens file."""
    logger.info("Loading tokens from %s", path.name)
    return Credentials.from_authorized_user_file(str(path), SCOPES)


def _extract_localhost_ports(client_secrets_path: Path) -> list[int]:
    """Extract localhost ports from client secrets redirect URIs."""
    data = json.loads(client_secrets_path.read_text())
    config = data.get("installed") or data.get("web") or {}
    redirect_uris = config.get("redirect_uris", [])

    ports: list[int] = []
    for uri in redirect_uris:
        parsed = urllib.parse.urlparse(uri)
        if parsed.hostname in LOCALHOST_HOSTS:
            if parsed.port is not None:
                ports.append(parsed.port)
            else:
                default_ports = {"http": 80, "https": 443}
                ports.append(default_ports.get(parsed.scheme, 80))
    return ports


def run_oauth_flow(client_secrets_path: Path) -> Credentials:
    """Run OAuth installed app flow with port retry. Returns credentials."""
    ports = _extract_localhost_ports(client_secrets_path)

    if not ports:
        logger.debug("No localhost ports found in redirect URIs, using default")
        ports = [8080]

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), scopes=SCOPES)

    failed_ports: list[int] = []
    for i, port in enumerate(ports):
        try:
            logger.debug("Starting OAuth server on port %d", port)
            return flow.run_local_server(port=port)
        except OSError as e:
            if e.errno != errno.EADDRINUSE:
                raise
            failed_ports.append(port)
            if i + 1 < len(ports):
                logger.info("Port %d is in use, trying %d...", port, ports[i + 1])

    raise PortsAlreadyInUseError(failed_ports=failed_ports)


def save_tokens(cwd: Path, creds: Credentials) -> Path:
    """Save credentials to a tokens file. Returns the path written."""
    suffix = creds.client_id.split(".")[0] if creds.client_id else "default"
    filename = f"credentials.{suffix}.json"
    filepath = cwd / filename
    filepath.write_text(creds.to_json())
    logger.info("Tokens saved to %s", filename)
    return filepath
