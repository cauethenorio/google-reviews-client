import json
import logging
from pathlib import Path

import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from google_reviews_client.constants import SCOPES

logger = logging.getLogger(__name__)

TOKENS_GLOBS = ("credentials.*.json",)
CLIENT_SECRETS_GLOBS = ("client_secret*.json", "*_client_secret*.json")


class MultipleFilesFoundError(Exception):
    def __init__(self, files_found: list[Path]):
        self.files_found = files_found
        super().__init__(f"Multiple files found: {files_found}")


class NoFilesFoundError(Exception):
    pass


class NotInstalledAppError(Exception):
    pass


def find_files(cwd: Path, globs: tuple[str, ...], explicit_path: Path | None = None) -> Path:
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
    return find_files(cwd, TOKENS_GLOBS, explicit_path)


def find_client_secrets_files(cwd: Path, explicit_path: Path | None = None) -> Path:
    """Find a client secrets file (client_secret*.json)."""
    return find_files(cwd, CLIENT_SECRETS_GLOBS, explicit_path)


def load_tokens(path: Path) -> Credentials:
    """Load credentials from a tokens file."""
    logger.info("Loading tokens from %s", path.name)
    return Credentials.from_authorized_user_file(str(path), SCOPES)


def run_oauth_flow(client_secrets_path: Path) -> Credentials:
    """Run OAuth flow for an installed (desktop) app. Returns credentials.

    Uses port=0 to let the OS pick any available port.
    Only installed (desktop) apps are supported — Google allows any localhost
    port for installed apps per RFC 8252.
    """
    data = json.loads(client_secrets_path.read_text())
    if "installed" not in data:
        raise NotInstalledAppError()

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), scopes=SCOPES)
    return flow.run_local_server(port=0)


USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def fetch_user_info(creds: Credentials) -> tuple[str, str] | None:
    """Fetch the authenticated user's name and email from Google.

    Returns (name, email) or None if the userinfo endpoint is unavailable
    (e.g., old tokens without openid/email scopes).
    """
    try:
        resp = httpx.get(USERINFO_URL, headers={"Authorization": f"Bearer {creds.token}"})
        if not resp.is_success:
            logger.debug("Userinfo request failed with status %d", resp.status_code)
            return None
        data = resp.json()
        return data.get("name", ""), data.get("email", "")
    except httpx.HTTPError:
        logger.debug("Userinfo request failed", exc_info=True)
        return None


def save_tokens(cwd: Path, creds: Credentials, *, email: str | None = None) -> Path:
    """Save credentials to a tokens file. Returns the path written.

    Filename format: credentials.{project_number}.{email}.json
    Falls back to credentials.{project_number}.json if email is unavailable.
    """
    project_number = creds.client_id.split("-")[0] if creds.client_id else "default"
    suffix = f"{project_number}.{email.lower()}" if email else project_number
    filename = f"credentials.{suffix}.json"
    filepath = cwd / filename
    filepath.write_text(creds.to_json())
    logger.info("Tokens saved to %s", filename)
    return filepath
