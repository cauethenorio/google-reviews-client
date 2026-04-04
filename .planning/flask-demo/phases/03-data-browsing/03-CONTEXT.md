# Phase 3: Data Browsing - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Authenticated users can navigate the full accounts → locations → reviews hierarchy and see meaningful errors. Routes follow a resource-based URL pattern. The landing page becomes conditional (authenticated vs not). The OAuth callback shows a success message before redirecting.

</domain>

<decisions>
## Implementation Decisions

### Route Structure (user-specified)
- **D-01:** `/` is conditional — if authenticated: list accounts; if not authenticated: show landing page (sign-in button, trust statement, feature list from Phase 2)
- **D-02:** OAuth callback shows a success message page with `<meta http-equiv="refresh" content="3;url=/">` — user sees "Authenticated successfully!" then auto-redirects to `/` after 3 seconds
- **D-03:** `/account/<account_id>` shows account details (name, type) and lists all locations for that account
- **D-04:** `/location/<location_id>` shows location details (title, address) and a "View Reviews" button linking to `/location/<location_id>/reviews`
- **D-05:** `/location/<location_id>/reviews` lists all reviews for the location with pagination

### API Integration
- **D-06:** Thin helper module (`api.py` or `helpers.py`) wraps credential reconstruction from Fernet cookie + GoogleReviewsClient instantiation into a `get_client(request)` function — routes call helper, not inline construction
- **D-07:** Credentials reconstructed from cookie's `access_token`, `refresh_token`, `expiry` using `google.oauth2.credentials.Credentials()` constructor
- **D-08:** Token refresh: if API call fails with 401 (AuthenticationError), redirect to `/login` to re-authenticate. Simpler approach — user re-auths rather than transparent refresh

### Error Handling
- **D-09:** Inline error banners on the same page (reuse Phase 2 error alert pattern with `role="alert"` and red styling)
- **D-10:** Contextual error messages per exception type:
  - `AuthenticationError` (401): "Your session has expired. Please sign in again." + link to `/login`
  - `GooglePermissionError` (403): "You don't have permission to access this resource." + link back to `/`
  - `RateLimitError` (429): "Too many requests. Please try again in a few moments." + retry link
  - `NotFoundError` (404): "Resource not found." + link back to `/`
  - `GoogleAPIError` (5xx): "Google is temporarily unavailable. Please try again later." + retry link

### Page Layout and Navigation
- **D-11:** Styled breadcrumb component with separators — e.g., `Accounts › Business Name › Location Name › Reviews`. Each segment is a clickable link back.
- **D-12:** Minimal information density per list item:
  - Accounts: name + type
  - Locations: title (+ address if available from Location model — note: current model has `title` and `store_code` but no address field)
  - Reviews: star rating + comment preview (truncated) + author name + date
- **D-13:** Friendly empty state messages with context:
  - No accounts: "No accounts found — make sure your Google account has access to a Business Profile."
  - No locations: "No locations found for this account."
  - No reviews: "No reviews yet for this location."

### Pagination
- **D-14:** Reviews only — "Next page" link at bottom with `?page_token=<token>` in URL. No "Previous" (API doesn't support backward pagination). Stateless, bookmarkable.
- **D-15:** Accounts and locations show all results without pagination (most users have few of each)

### Claude's Discretion
- Exact breadcrumb separator styling and Tailwind classes
- Review comment truncation length for list view
- Success page layout and styling for callback redirect
- How to pass account/location names through the breadcrumb chain (URL params, extra API calls, or template context)
- Whether `/location/<location_id>` needs the account_id in the URL for API calls (GoogleReviewsClient.list_locations needs account name)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Library client (API integration)
- `src/google_reviews_client/client.py` — GoogleReviewsClient class with list_accounts(), list_locations(account), list_reviews(location) methods
- `src/google_reviews_client/models.py` — Account, Location, Review, Reviewer, StarRating, ReviewReply dataclasses
- `src/google_reviews_client/exceptions.py` — AuthenticationError, GooglePermissionError, RateLimitError, NotFoundError, GoogleAPIError
- `src/google_reviews_client/constants.py` — ACCOUNT_MGMT_BASE, BUSINESS_BASE, SCOPES

### Flask app (Phase 1+2 foundation)
- `flask-example/auth.py` — OAuth routes, login_required decorator, Fernet cookie handling
- `flask-example/views.py` — Current routes (/, /accounts placeholder)
- `flask-example/cookies.py` — encrypt_tokens(), decrypt_tokens(), TOKEN_COOKIE_NAME
- `flask-example/app.py` — App factory, config keys (FERNET, GOOGLE_CLIENT_ID, etc.)
- `flask-example/templates/base.html` — Base template with Tailwind CDN, conditional nav

### Research
- `.planning/flask-demo/research/PITFALLS.md` — Cookie size constraints, SameSite behavior
- `.planning/flask-demo/research/ARCHITECTURE.md` — Auth blueprint design, cookie write flow

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GoogleReviewsClient`: Full API client with list_accounts/list_locations/list_reviews — ready to use from Flask routes
- `Account`, `Location`, `Review` dataclasses: Rich models with from_api_response() class methods
- `login_required` decorator: Already checks Fernet cookie for auth_status=authenticated
- Phase 2 error alert pattern: `role="alert"` banners in `index.html` — reuse for API errors
- `base.html`: Tailwind CDN template with conditional logout nav

### Established Patterns
- Fernet cookie stores `access_token`, `refresh_token`, `expiry` after OAuth callback
- Blueprint-based route organization (auth_bp, views_bp)
- Fail-fast env var validation at startup

### Integration Points
- `views.py`: Replace placeholder `/accounts` route, add `/account/<id>`, `/location/<id>`, `/location/<id>/reviews`
- `auth.py`: Update callback to render success page instead of direct redirect
- New `api.py`: Helper to reconstruct Credentials from cookie and create GoogleReviewsClient
- New templates: `accounts.html` (update existing), `account.html`, `location.html`, `reviews.html`, `callback_success.html`
- `index.html`: Update to conditionally show accounts list when authenticated

</code_context>

<specifics>
## Specific Ideas

- User explicitly specified the route structure: `/`, `/account/<id>`, `/location/<id>`, `/location/<id>/reviews`
- Callback must show success message for 3 seconds before redirecting — not an instant redirect
- Landing page and accounts list share the `/` route with conditional rendering based on auth state

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-data-browsing*
*Context gathered: 2026-04-04*
