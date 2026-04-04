"""Flask application factory with fail-fast env var validation."""

import base64
import hashlib
import os

from cryptography.fernet import Fernet
from flask import Flask

REQUIRED_ENV_VARS = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "SECRET_KEY"]


def _check_required_env_vars():
    """Crash with a clear message if any required env var is missing."""
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            msg = f"Required environment variable {var} is not set. See .env.example."
            raise RuntimeError(msg)


def _make_fernet_key(secret: str) -> bytes:
    """Derive a valid Fernet key from an arbitrary secret string."""
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def create_app():
    """Application factory."""
    _check_required_env_vars()

    app = Flask(__name__)
    app.secret_key = os.environ["SECRET_KEY"]
    app.config["FERNET"] = Fernet(_make_fernet_key(os.environ["SECRET_KEY"]))
    app.config["GOOGLE_CLIENT_ID"] = os.environ["GOOGLE_CLIENT_ID"]
    app.config["GOOGLE_CLIENT_SECRET"] = os.environ["GOOGLE_CLIENT_SECRET"]

    from auth import auth_bp  # noqa: PLC0415
    from views import views_bp  # noqa: PLC0415

    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)

    return app
