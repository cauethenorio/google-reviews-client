import json
import logging
from pathlib import Path

import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from google_reviews_client.constants import SCOPES

logger = logging.getLogger(__name__)

CLIENT_SECRETS_GLOBS = ("client_secret*.json", "*_client_secret*.json")

USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class NotInstalledAppError(Exception):
    pass


def find_client_secrets_files(cwd: Path, explicit_path: Path | None = None) -> Path:
    """Find a client secrets file (client_secret*.json).

    Returns the single matching Path.
    Raises FileNotFoundError if not found or if explicit path doesn't exist.
    Raises ValueError if multiple matches found.
    """
    if explicit_path is not None:
        if not explicit_path.is_file():
            msg = f"File not found: {explicit_path}"
            raise FileNotFoundError(msg)
        logger.info("Using specified file: %s", explicit_path)
        return explicit_path

    matches: list[Path] = []
    for pattern in CLIENT_SECRETS_GLOBS:
        logger.debug("Searching for %s in %s", pattern, cwd)
        matches.extend(cwd.glob(pattern))

    if len(matches) == 1:
        logger.info("Found %s", matches[0].name)
        return matches[0]

    if len(matches) == 0:
        msg = "No client secrets files found. Expected: client_secret*.json"
        raise FileNotFoundError(msg)

    files_str = ", ".join(str(p.name) for p in sorted(matches))
    msg = f"Multiple client secrets files found: {files_str}. Use --client-secrets-file to specify."
    raise ValueError(msg)


def run_oauth_flow(client_secrets_path: Path) -> Credentials:
    """Run OAuth flow for an installed (desktop) app. Returns credentials.

    Uses port=0 to let the OS pick any available port.
    Only installed (desktop) apps are supported.
    """
    data = json.loads(client_secrets_path.read_text())
    if "installed" not in data:
        raise NotInstalledAppError()

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), scopes=SCOPES)
    return flow.run_local_server(port=0)


def fetch_user_info(creds: Credentials) -> tuple[str, str] | None:
    """Fetch the authenticated user's name and email from Google.

    Returns (name, email) or None if unavailable.
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


def credentials_from_config_data(data: dict) -> Credentials:
    """Create Credentials from config file credentials dict."""
    return Credentials.from_authorized_user_info(data, SCOPES)


def credentials_to_config_data(creds: Credentials) -> dict:
    """Convert Credentials to a dict for config file storage."""
    return json.loads(creds.to_json())
