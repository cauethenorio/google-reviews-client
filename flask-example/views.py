"""Views blueprint with index and accounts routes."""

from flask import Blueprint, render_template, request

from auth import login_required

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Landing page with sign-in button, trust statement, and error display."""
    return render_template("index.html", error=request.args.get("error"))


@views_bp.route("/accounts")
@login_required
def accounts():
    """Placeholder accounts page behind login_required."""
    return render_template("accounts.html", show_logout=True)
