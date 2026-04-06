"""Views blueprint with data browsing routes and error handling."""

from api import get_all_reviews, get_client, get_reviews_page
from auth import login_required
from cookies import TOKEN_COOKIE_NAME, decrypt_tokens
from flask import Blueprint, Response, redirect, render_template, request

from google_reviews_client.exceptions import (
    AuthenticationError,
    GoogleAPIError,
    GooglePermissionError,
    NotFoundError,
    RateLimitError,
)
from google_reviews_client.models import Account

views_bp = Blueprint("views", __name__)


def _error_context(exc, back_url="/", back_text="Back to accounts"):
    """Map library exception to error dict for template rendering."""
    if isinstance(exc, GooglePermissionError):
        return {
            "message": "You don't have permission to access this resource.",
            "link": "/",
            "link_text": "Back to accounts",
        }
    if isinstance(exc, RateLimitError):
        return {"message": "Too many requests. Please try again in a few moments.", "retry": True}
    if isinstance(exc, NotFoundError):
        return {"message": "Resource not found.", "link": "/", "link_text": "Back to accounts"}
    # GoogleAPIError (5xx) or any other
    return {"message": "Google is temporarily unavailable. Please try again later.", "retry": True}


@views_bp.route("/")
def index():
    """Landing page for unauthenticated users, accounts list for authenticated."""
    from flask import current_app

    cookie = request.cookies.get(TOKEN_COOKIE_NAME)
    if cookie:
        data = decrypt_tokens(cookie, current_app.config["FERNET"])
        if data is not None and data.get("auth_status") == "authenticated":
            client = get_client()
            if client is None:
                return redirect("/login")
            try:
                accounts = client.list_accounts()
            except AuthenticationError:
                return redirect("/login")
            except (GooglePermissionError, RateLimitError, NotFoundError, GoogleAPIError) as exc:
                return render_template("accounts.html", error=_error_context(exc), accounts=[], show_logout=True)
            if len(accounts) == 1:
                return redirect(f"/account/{accounts[0].name.split('/')[-1]}")
            return render_template("accounts.html", accounts=accounts, show_logout=True)

    return render_template("index.html", error=request.args.get("error"))


@views_bp.route("/account/<account_id>")
@login_required
def account_detail(account_id):
    """Show locations for a specific account."""
    client = get_client()
    if client is None:
        return redirect("/login")

    account_name = f"accounts/{account_id}"

    try:
        accounts = client.list_accounts()
        account = next((acc for acc in accounts if acc.name == account_name), None)
        if account is None:
            account = Account(name=account_name, account_name=account_id)

        locations = client.list_locations(account_name)
    except AuthenticationError:
        return redirect("/login")
    except (GooglePermissionError, RateLimitError, NotFoundError, GoogleAPIError) as exc:
        account = Account(name=account_name, account_name=account_id)
        breadcrumbs = [{"label": "Accounts", "url": "/"}, {"label": account.account_name, "url": ""}]
        return render_template(
            "account.html",
            error=_error_context(exc),
            account=account,
            locations=[],
            breadcrumbs=breadcrumbs,
            show_logout=True,
        )

    if len(locations) == 1:
        loc = locations[0]
        return redirect(f"/account/{account_id}/location/{loc.location_id}")

    breadcrumbs = [{"label": "Accounts", "url": "/"}, {"label": account.account_name, "url": ""}]
    return render_template(
        "account.html", account=account, locations=locations, breadcrumbs=breadcrumbs, show_logout=True
    )


@views_bp.route("/account/<account_id>/location/<location_id>")
@login_required
def location_detail(account_id, location_id):
    """Show details for a specific location."""
    client = get_client()
    if client is None:
        return redirect("/login")

    account_name = f"accounts/{account_id}"

    try:
        accounts = client.list_accounts()
        account = next((acc for acc in accounts if acc.name == account_name), None)
        if account is None:
            account = Account(name=account_name, account_name=account_id)

        locations = client.list_locations(account_name)
        location = next((loc for loc in locations if loc.location_id == location_id), None)
        if location is None:
            return render_template(
                "location.html",
                error={"message": "Resource not found.", "link": "/", "link_text": "Back to accounts"},
                location=Account(name="", account_name=""),  # dummy for template
                account=account,
                breadcrumbs=[
                    {"label": "Accounts", "url": "/"},
                    {"label": account.account_name, "url": f"/account/{account_id}"},
                    {"label": "Location", "url": ""},
                ],
                show_logout=True,
            )
    except AuthenticationError:
        return redirect("/login")
    except (GooglePermissionError, RateLimitError, NotFoundError, GoogleAPIError) as exc:
        account = Account(name=account_name, account_name=account_id)
        breadcrumbs = [
            {"label": "Accounts", "url": "/"},
            {"label": account.account_name, "url": f"/account/{account_id}"},
            {"label": "Location", "url": ""},
        ]
        return render_template(
            "location.html",
            error=_error_context(exc),
            location=Account(name="", account_name=""),
            account=account,
            breadcrumbs=breadcrumbs,
            show_logout=True,
        )

    breadcrumbs = [
        {"label": "Accounts", "url": "/"},
        {"label": account.account_name, "url": f"/account/{account_id}"},
        {"label": location.title or "Location", "url": ""},
    ]
    return render_template(
        "location.html", location=location, account=account, breadcrumbs=breadcrumbs, show_logout=True
    )


@views_bp.route("/account/<account_id>/location/<location_id>/reviews")
@login_required
def reviews(account_id, location_id):
    """Show paginated reviews for a location."""
    page_token = request.args.get("page_token")

    client = get_client()
    if client is None:
        return redirect("/login")

    account_name = f"accounts/{account_id}"
    location_name = f"accounts/{account_id}/locations/{location_id}"

    try:
        accounts = client.list_accounts()
        account = next((acc for acc in accounts if acc.name == account_name), None)
        if account is None:
            account = Account(name=account_name, account_name=account_id)

        locations = client.list_locations(account_name)
        location = next((loc for loc in locations if loc.location_id == location_id), None)

        review_list, next_token, total_review_count, average_rating = get_reviews_page(
            client, location_name, page_token
        )
    except AuthenticationError:
        return redirect("/login")
    except (GooglePermissionError, RateLimitError, NotFoundError, GoogleAPIError) as exc:
        account = Account(name=account_name, account_name=account_id)
        breadcrumbs = [
            {"label": "Accounts", "url": "/"},
            {"label": account.account_name, "url": f"/account/{account_id}"},
            {"label": "Location", "url": f"/account/{account_id}/location/{location_id}"},
            {"label": "Reviews", "url": ""},
        ]
        from google_reviews_client.models import Location

        location = Location(name="", location_id=location_id, account_id=account_id)
        return render_template(
            "reviews.html",
            error=_error_context(exc),
            reviews=[],
            location=location,
            account=account,
            breadcrumbs=breadcrumbs,
            next_page_token=None,
            total_review_count=None,
            average_rating=None,
            avg_rounded=0,
            show_logout=True,
        )

    if location is None:
        from google_reviews_client.models import Location

        location = Location(name="", location_id=location_id, account_id=account_id)

    breadcrumbs = [
        {"label": "Accounts", "url": "/"},
        {"label": account.account_name, "url": f"/account/{account_id}"},
        {"label": location.title or "Location", "url": f"/account/{account_id}/location/{location_id}"},
        {"label": "Reviews", "url": ""},
    ]
    avg_rounded = round(average_rating) if average_rating else 0
    return render_template(
        "reviews.html",
        reviews=review_list,
        location=location,
        account=account,
        breadcrumbs=breadcrumbs,
        next_page_token=next_token,
        total_review_count=total_review_count,
        average_rating=average_rating,
        avg_rounded=avg_rounded,
        show_logout=True,
    )


@views_bp.route("/account/<account_id>/location/<location_id>/reviews/download")
@login_required
def download_reviews(account_id, location_id):
    """Download all reviews for a location as a JSON zip file."""
    import io
    import json
    import zipfile

    client = get_client()
    if client is None:
        return redirect("/login")

    location_name = f"accounts/{account_id}/locations/{location_id}"

    try:
        all_reviews = get_all_reviews(client, location_name)
    except AuthenticationError:
        return redirect("/login")
    except (GooglePermissionError, RateLimitError, NotFoundError, GoogleAPIError):
        return redirect(f"/account/{account_id}/location/{location_id}/reviews")

    reviews_data = [
        {
            "reviewer": review.reviewer.display_name,
            "rating": review.rating_value,
            "comment": review.comment,
            "date": review.create_time.isoformat() if review.create_time else None,
            "reply": review.review_reply.comment if review.has_reply else None,
        }
        for review in all_reviews
    ]

    export = {
        "location": location_name,
        "exported_at": __import__("datetime").datetime.now().isoformat(),
        "total_reviews": len(reviews_data),
        "reviews": reviews_data,
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("reviews.json", json.dumps(export, indent=2, ensure_ascii=False))
    buf.seek(0)

    return Response(
        buf.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment; filename=reviews.json.zip"},
    )
