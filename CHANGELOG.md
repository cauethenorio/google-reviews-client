# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-04-03

### Breaking Changes

- `PermissionError` renamed to `GooglePermissionError`

### Added

- Retry with exponential backoff in HTTP client
- `__version__` attribute exposed in the package
- Python 3.14 support

### Improved

- Complete docstrings on all public modules, classes, and methods
- Significantly expanded test coverage
- Restructured dependencies and build configuration
- README updated with correct exception names

## [0.2.0] - 2026-03-20

### Changed

- CLI command renamed from `google-reviews` to `google-reviews-client`
- `click` is now an optional dependency — install with `pip install google-reviews-client[cli]`
- CLI can be run directly with `uvx 'google-reviews-client[cli]'` without installing

## [0.1.0] - 2026-03-20

### Added

- `GoogleReviewsClient` with `list_accounts()`, `list_locations()`, and `list_reviews()` methods
- Typed data models: `Account`, `Location`, `Review`, `Reviewer`, `ReviewReply`, `StarRating`
- Lazy pagination for reviews (fetches pages on demand)
- Incremental sync with early exit (orders by `updateTime desc`, stops when caught up)
- Typed exceptions: `AuthenticationError`, `RateLimitError`, `NotFoundError`, `PermissionError`, `GoogleAPIError`
- CLI (`google-reviews-client`) with click-based interface:
  - Config files (`google-reviews-config.{project}.{email}.json`) storing credentials and targets
  - Multi-account and multi-location support with multi-select pickers
  - Auto-sync on subsequent runs (no prompts needed)
  - `--language` flag for review language (saved per-location in config)
  - `--verbose` flag for debug output (HTTP requests, file searches, full tracebacks)
  - Streaming table output with star emojis, auto-fit to terminal width
  - JSONL output with deduplication (new reviews appended, updated reviews replaced in-place)
  - Helpful error messages with clickable terminal links for quota, auth, and setup issues
  - `Accept-Language` header support to get reviews in original language
