"""Auth blueprint with OAuth 2.0 login, callback, logout, and login_required."""

import os
from functools import wraps

from flask import Blueprint, redirect, request, url_for, current_app
from google_auth_oauthlib.flow import Flow

from cookies import encrypt_tokens, decrypt_tokens, TOKEN_COOKIE_NAME, COOKIE_MAX_AGE

# Allow HTTP for local development (OAuthlib requires HTTPS by default)
if os.environ.get("FLASK_DEBUG"):
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SCOPES = ["https://www.googleapis.com/auth/business.manage"]

auth_bp = Blueprint("auth", __name__)


def _build_client_config(client_id, client_secret):
    """Build OAuth client config dict from credentials."""
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def login_required(f):
    """Decorator that checks for a valid authenticated cookie."""

    @wraps(f)
    def decorated(*args, **kwargs):
        cookie = request.cookies.get(TOKEN_COOKIE_NAME)
        if not cookie:
            return redirect("/?error=session_expired")

        data = decrypt_tokens(cookie, current_app.config["FERNET"])
        if data is None or data.get("auth_status") != "authenticated":
            return redirect("/?error=session_expired")

        return f(*args, **kwargs)

    return decorated


@auth_bp.route("/login")
def login():
    """Initiate Google OAuth 2.0 flow with PKCE."""
    client_config = _build_client_config(
        current_app.config["GOOGLE_CLIENT_ID"],
        current_app.config["GOOGLE_CLIENT_SECRET"],
    )

    redirect_uri = os.environ.get("REDIRECT_URI") or url_for(
        "auth.callback", _external=True
    )

    flow = Flow.from_client_config(
        client_config, scopes=SCOPES, redirect_uri=redirect_uri
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline", prompt="consent"
    )

    pending_data = {
        "auth_status": "pending",
        "state": state,
        "verifier": flow.code_verifier,
    }
    encrypted = encrypt_tokens(pending_data, current_app.config["FERNET"])

    response = redirect(authorization_url)
    response.set_cookie(
        TOKEN_COOKIE_NAME,
        encrypted,
        httponly=True,
        secure=not current_app.debug,
        samesite="Lax",
        max_age=300,
    )
    return response


@auth_bp.route("/callback")
def callback():
    """Handle OAuth callback, exchange code for tokens."""
    cookie = request.cookies.get(TOKEN_COOKIE_NAME)
    if not cookie:
        return redirect("/?error=missing_state")

    pending = decrypt_tokens(cookie, current_app.config["FERNET"])
    if pending is None or pending.get("auth_status") != "pending":
        return redirect("/?error=invalid_state")

    if request.args.get("state") != pending["state"]:
        return redirect("/?error=state_mismatch")

    if "error" in request.args:
        return redirect(f"/?error={request.args['error']}")

    client_config = _build_client_config(
        current_app.config["GOOGLE_CLIENT_ID"],
        current_app.config["GOOGLE_CLIENT_SECRET"],
    )

    redirect_uri = os.environ.get("REDIRECT_URI") or url_for(
        "auth.callback", _external=True
    )

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        state=pending["state"],
        code_verifier=pending["verifier"],
        autogenerate_code_verifier=False,
    )

    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    token_data = {
        "auth_status": "authenticated",
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }
    encrypted = encrypt_tokens(token_data, current_app.config["FERNET"])

    response = redirect("/accounts")
    response.set_cookie(
        TOKEN_COOKIE_NAME,
        encrypted,
        httponly=True,
        secure=not current_app.debug,
        samesite="Lax",
        max_age=COOKIE_MAX_AGE,
    )
    return response


@auth_bp.route("/logout")
def logout():
    """Clear auth cookie and redirect to landing page."""
    response = redirect("/")
    response.delete_cookie(TOKEN_COOKIE_NAME)
    return response
