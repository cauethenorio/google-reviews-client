# Phase 3: Data Browsing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 03-data-browsing
**Areas discussed:** API integration approach, Error handling UX, Page layout and navigation, Pagination approach

---

## API Integration Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Direct library use | Each route reconstructs Credentials inline, creates GoogleReviewsClient directly | |
| Thin helper module | A helpers.py wraps credential reconstruction + client creation into get_client() | ✓ |
| You decide | Claude picks during planning | |

**User's choice:** Thin helper module
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Transparent refresh in decorator | Enhance @login_required to detect refreshed credentials after route runs | |
| Catch and redirect | If API call fails with 401, redirect to /login to re-authenticate | ✓ |
| You decide | Claude picks during planning | |

**User's choice:** Catch and redirect
**Notes:** Simpler approach preferred for demo app

---

## Error Handling UX

| Option | Description | Selected |
|--------|-------------|----------|
| Inline error on same page | Styled error banner at top of current page | ✓ |
| Dedicated error page | Redirect to full error page with explanation and action buttons | |
| You decide | Claude picks during planning | |

**User's choice:** Inline error on same page

| Option | Description | Selected |
|--------|-------------|----------|
| Contextual per error type | Different messages and actions for 401, 403, 429, 503, 404 | ✓ |
| Generic retry + home | All errors show 'Try again' and 'Back to home' | |
| You decide | Claude picks during planning | |

**User's choice:** Contextual per error type

---

## Page Layout and Navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Text breadcrumb trail | Simple clickable text with › separators | |
| Styled breadcrumb component | More polished breadcrumb with separators, icons, or background styling | ✓ |
| You decide | Claude picks during planning | |

**User's choice:** Styled breadcrumb component

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal with key details | Accounts: name+type. Locations: title+address. Reviews: rating+preview+author+date | ✓ |
| Rich with all available data | Show everything the API returns | |
| You decide | Claude picks during planning | |

**User's choice:** Minimal with key details

| Option | Description | Selected |
|--------|-------------|----------|
| Friendly message with context | Explanatory message per empty state | ✓ |
| Simple 'no results' text | Just 'No items to display' everywhere | |
| You decide | Claude picks during planning | |

**User's choice:** Friendly message with context

---

## Pagination Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Next page link with URL param | nextPageToken as ?page_token= in URL, stateless | ✓ |
| Load more button (JS) | Append results without page reload | |
| You decide | Claude picks during planning | |

**User's choice:** Next page link with URL param

| Option | Description | Selected |
|--------|-------------|----------|
| Show all | Accounts and locations show all results, no pagination | ✓ |
| Paginate everything | Apply pagination to all lists | |

**User's choice:** Show all for accounts and locations

---

## Route Structure (user-specified)

User provided exact route structure mid-discussion:

- `/` — conditional: authenticated shows accounts, unauthenticated shows landing page
- OAuth callback — success message page with 3-second meta refresh redirect to `/`
- `/account/<account_id>` — account details + locations list
- `/location/<location_id>` — location details + "View Reviews" button
- `/location/<location_id>/reviews` — reviews list with pagination

| Option | Description | Selected |
|--------|-------------|----------|
| / com lógica condicional | Authenticated: accounts. Not authenticated: landing page | ✓ |
| Landing em /welcome | Separate landing route | |
| Manter / como landing | Keep current structure | |

| Option | Description | Selected |
|--------|-------------|----------|
| HTML meta refresh | Page with meta http-equiv='refresh' for 3s redirect | ✓ |
| JavaScript setTimeout | JS-based redirect after 3 seconds | |

---

## Claude's Discretion

- Breadcrumb separator styling and Tailwind classes
- Review comment truncation length
- Success page layout
- Breadcrumb name passing strategy
- URL structure for location routes (whether account_id is needed)
