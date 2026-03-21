# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-03-20

### Added

- `GoogleReviewsClient` with `list_accounts()`, `list_locations()`, and `list_reviews()` methods
- Typed data models: `Account`, `Location`, `Review`, `Reviewer`, `ReviewReply`, `StarRating`
- Lazy pagination for reviews (fetches pages on demand)
- Incremental sync with early exit (orders by `updateTime desc`, stops when caught up)
- Typed exceptions: `AuthenticationError`, `RateLimitError`, `NotFoundError`, `PermissionError`, `GoogleAPIError`
- CLI (`google-reviews-download`) with click-based interface:
  - Config files (`google-reviews-config.{project}.{email}.json`) storing credentials and targets
  - Multi-account and multi-location support with multi-select pickers
  - Auto-sync on subsequent runs (no prompts needed)
  - `--language` flag for review language (saved per-location in config)
  - `--verbose` flag for debug output (HTTP requests, file searches, full tracebacks)
  - Streaming table output with star emojis, auto-fit to terminal width
  - JSONL output with deduplication (new reviews appended, updated reviews replaced in-place)
  - Helpful error messages with clickable terminal links for quota, auth, and setup issues
  - `Accept-Language` header support to get reviews in original language
