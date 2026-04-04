# Roadmap: Flask Demo App

## Overview

A four-phase delivery that takes the project from a bare Flask skeleton to a polished, publicly-hostable demo. Phase 1 lays the encrypted-cookie foundation that everything else depends on. Phase 2 completes the full OAuth lifecycle so users can sign in and sign out. Phase 3 wires in the Google Business Profile API to deliver the core browsing flow (accounts → locations → reviews). Phase 4 adds the UX completeness that makes the demo convincing: visual star ratings, reviewer photos, the library snippet, and the review summary.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Flask app skeleton, Fernet cookie encryption, env var config, stateless infrastructure
- [ ] **Phase 2: Auth and Landing** - OAuth 2.0 login/callback/logout, encrypted token cookie, landing page with trust statement
- [ ] **Phase 3: Data Browsing** - Accounts, locations, and reviews pages with pagination, breadcrumbs, and error handling
- [ ] **Phase 4: Polish** - Star ratings, reviewer photos, review summary, library snippet

## Phase Details

### Phase 1: Foundation
**Goal**: A running Flask app with Fernet encryption and env var config that future phases build on
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. `flask run` starts the app with no errors when `.env` is populated from `.env.example`
  2. `cookies.py` correctly encrypts and decrypts a token dict using a Fernet key derived from `SECRET_KEY`
  3. App refuses to start with a clear error message when required env vars are absent
  4. No database, no files, no server-side session storage — only cookie and URL state exist in the design
**Plans**: 2 plans
Plans:
- [ ] 01-01-PLAN.md — Project scaffold, app factory, cookie module, blueprints, templates
- [ ] 01-02-PLAN.md — Test suite for env var validation, cookie encryption, index route

### Phase 2: Auth and Landing
**Goal**: Users can sign in with Google, have their tokens stored in an encrypted cookie, and sign out
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, UX-01, UX-02
**Success Criteria** (what must be TRUE):
  1. Landing page loads at `/` with a "Sign in with Google" button and a visible "no data stored" statement
  2. Clicking sign-in redirects to Google's OAuth consent screen with PKCE and state parameter present
  3. After authorizing, user is redirected back and lands on the accounts page (cookie set, no server session)
  4. Logging out clears the cookie and returns the user to the landing page
  5. Visiting a protected page with an expired or missing token redirects to the landing page with a message
**Plans**: TBD
**UI hint**: yes

### Phase 3: Data Browsing
**Goal**: Authenticated users can navigate the full accounts → locations → reviews hierarchy and see meaningful errors
**Depends on**: Phase 2
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, UX-05
**Success Criteria** (what must be TRUE):
  1. Accounts page lists all Google Business Profile accounts the authenticated user has access to
  2. Clicking an account shows its locations with name and address
  3. Clicking a location shows its reviews with star rating, text, author, date, and any reply
  4. Reviews spanning multiple pages show a "Next" link; navigating pages works via `nextPageToken` in the URL
  5. Empty accounts, locations, or reviews pages show an explanatory message instead of a blank list
  6. API errors (403, 429, 503) show a human-readable error page with retry or re-auth options
**Plans**: TBD
**UI hint**: yes

### Phase 4: Polish
**Goal**: The demo is visually complete and demonstrates the library's value clearly
**Depends on**: Phase 3
**Requirements**: UX-03, UX-04, UX-06, UX-07
**Success Criteria** (what must be TRUE):
  1. Star ratings display as Unicode stars (e.g., ★★★★☆) rather than a number
  2. Reviewer photos appear next to each review with a fallback for anonymous reviewers
  3. Reviews page shows total review count and average rating summary sourced from the API response
  4. A copy-pasteable code snippet showing how to use the library appears at the bottom of the reviews page
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Planning complete | - |
| 2. Auth and Landing | 0/? | Not started | - |
| 3. Data Browsing | 0/? | Not started | - |
| 4. Polish | 0/? | Not started | - |
