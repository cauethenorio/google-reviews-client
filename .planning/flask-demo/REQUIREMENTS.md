# Requirements: Flask Demo App

**Defined:** 2026-04-03
**Core Value:** Let potential users try the library instantly — no setup, no database, no data stored

## v1 Requirements

### Authentication

- [x] **AUTH-01**: User can sign in with Google via OAuth 2.0 with PKCE and state parameter
- [x] **AUTH-02**: OAuth callback exchanges code for tokens and stores them in a Fernet-encrypted cookie
- [x] **AUTH-03**: User can log out, clearing the encrypted cookie
- [x] **AUTH-04**: Expired or invalid tokens are detected and user is redirected to re-authenticate with a clear message

### Data Browsing

- [x] **DATA-01**: User can view a list of all Google Business Profile accounts they have access to
- [x] **DATA-02**: User can click an account to view its locations with name and address
- [x] **DATA-03**: User can click a location to view its reviews with star rating, text, author, date, and replies
- [x] **DATA-04**: Reviews are paginated via nextPageToken passed as a URL query parameter
- [x] **DATA-05**: Empty states (no accounts, no locations, no reviews) show explanatory messages
- [x] **DATA-06**: API errors (403, 429, 503) show human-readable error pages with retry/re-auth options

### User Experience

- [x] **UX-01**: Landing page explains what the demo does and shows a "Sign in with Google" button
- [x] **UX-02**: Landing page includes a "no data stored" trust statement
- [ ] **UX-03**: Star ratings are displayed visually (★★★★☆)
- [ ] **UX-04**: Reviewer photos are displayed with fallback for anonymous reviewers
- [x] **UX-05**: Breadcrumb navigation shows Account → Location → Reviews hierarchy
- [ ] **UX-06**: Reviews page shows total review count and average rating summary
- [ ] **UX-07**: Reviews page shows a copy-pasteable library usage code snippet

### Infrastructure

- [x] **INFRA-01**: App is configured via env vars: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY
- [x] **INFRA-02**: App is fully stateless — no database, no files, no server-side sessions
- [x] **INFRA-03**: All navigation state lives in URL paths and query parameters

## v2 Requirements

### Deployment

- **DEPLOY-01**: HTTPS enforcement with SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SAMESITE=Lax
- **DEPLOY-02**: Gunicorn configuration for production hosting
- **DEPLOY-03**: ProxyFix middleware for PaaS hosting behind reverse proxy
- **DEPLOY-04**: Deployment documentation for Render/Railway/Fly.io

### Polish

- **POLISH-01**: orderBy toggle for reviews (newest first vs highest rated)
- **POLISH-02**: Google OAuth consent screen verification guide

## Out of Scope

| Feature | Reason |
|---------|--------|
| Write operations (reply to reviews) | Read-only demo; mutation on live data is risky in a public demo |
| Database or file storage | Contradicts stateless goal |
| User accounts / registration | Cookie session only, no user management |
| Refresh token storage in cookie | Higher security risk; access-token-only with re-auth is sufficient for a demo |
| JS framework (React, Vue) | Server-side Jinja2 templates are sufficient; no build pipeline needed |
| Search / filter reviews | GBP API doesn't support free-text search; adds complexity |
| Background jobs / polling | Requires task queue; contradicts stateless design |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 2 | Complete |
| AUTH-02 | Phase 2 | Complete |
| AUTH-03 | Phase 2 | Complete |
| AUTH-04 | Phase 2 | Complete |
| DATA-01 | Phase 3 | Complete |
| DATA-02 | Phase 3 | Complete |
| DATA-03 | Phase 3 | Complete |
| DATA-04 | Phase 3 | Complete |
| DATA-05 | Phase 3 | Complete |
| DATA-06 | Phase 3 | Complete |
| UX-01 | Phase 2 | Complete |
| UX-02 | Phase 2 | Complete |
| UX-03 | Phase 4 | Pending |
| UX-04 | Phase 4 | Pending |
| UX-05 | Phase 3 | Complete |
| UX-06 | Phase 4 | Pending |
| UX-07 | Phase 4 | Pending |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-04-03*
*Last updated: 2026-04-04 after plan 03-01 completion*
