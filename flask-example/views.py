"""Views blueprint with index route."""

from flask import Blueprint, render_template

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Simple index page confirming the app is running."""
    return render_template("index.html")
