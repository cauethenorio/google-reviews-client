"""Tests for CLI helper functions (formatting, display, JSONL operations)."""

import json
from datetime import datetime, timezone

from google_reviews_client.cli import (
    display_width,
    extract_project_number,
    format_stars,
    get_comment_width,
    pad_to_width,
    print_review_row,
    print_reviews_table_header,
    read_jsonl_metadata,
    sync_reviews_jsonl,
    terminal_link,
    truncate_to_width,
    write_reviews_jsonl,
)
from google_reviews_client.models import Review, Reviewer, StarRating


def _make_review(
    review_id="r1",
    rating=StarRating.FIVE,
    comment="Great place",
    reviewer_name="Alice",
    has_reply=False,
    create_time=None,
    update_time=None,
):
    create_time = create_time or datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
    update_time = update_time or create_time
    return Review(
        review_id=review_id,
        reviewer=Reviewer(display_name=reviewer_name),
        star_rating=rating,
        comment=comment,
        create_time=create_time,
        update_time=update_time,
        review_reply=None if not has_reply else _make_reply(),
    )


def _make_reply():
    from google_reviews_client.models import ReviewReply

    return ReviewReply(comment="Thanks!", update_time=datetime(2025, 1, 16, tzinfo=timezone.utc))


class TestDisplayWidth:
    def test_ascii(self):
        assert display_width("hello") == 5

    def test_wide_chars(self):
        # CJK characters are 2 columns wide
        assert display_width("你好") == 4

    def test_mixed(self):
        assert display_width("hi你") == 4

    def test_empty(self):
        assert display_width("") == 0


class TestTruncateToWidth:
    def test_short_string_unchanged(self):
        assert truncate_to_width("hello", 10) == "hello"

    def test_long_string_truncated(self):
        result = truncate_to_width("a very long string here", 10)
        assert result.endswith("...")
        assert display_width(result) <= 10

    def test_wide_chars_truncated(self):
        result = truncate_to_width("你好世界测试", 10)
        assert result.endswith("...")
        assert display_width(result) <= 10


class TestPadToWidth:
    def test_pads_to_target(self):
        result = pad_to_width("hi", 5)
        assert result == "hi   "

    def test_no_pad_when_exact(self):
        result = pad_to_width("hello", 5)
        assert result == "hello"

    def test_no_pad_when_over(self):
        result = pad_to_width("hello!", 5)
        assert result == "hello!"


class TestFormatStars:
    def test_five_stars(self):
        result = format_stars(5)
        assert result.count("\u2b50") == 5

    def test_one_star(self):
        result = format_stars(1)
        assert result.count("\u2b50") == 1

    def test_zero_stars(self):
        result = format_stars(0)
        assert result.count("\u2b50") == 0


class TestExtractProjectNumber:
    def test_valid_client_id(self):
        assert extract_project_number("724219465644-xxx.apps.googleusercontent.com") == "724219465644"

    def test_none(self):
        assert extract_project_number(None) is None

    def test_non_numeric_prefix(self):
        assert extract_project_number("abc-xxx.apps.googleusercontent.com") is None


class TestTerminalLink:
    def test_creates_osc8_link(self):
        result = terminal_link("https://example.com", "click here")
        assert "https://example.com" in result
        assert "click here" in result
        assert "\033]8;;" in result


class TestGetCommentWidth:
    def test_returns_positive_int(self):
        width = get_comment_width()
        assert isinstance(width, int)
        assert width >= 20


class TestPrintReviewsTableHeader:
    def test_prints_header(self, capsys):
        print_reviews_table_header()
        output = capsys.readouterr().out
        assert "Date" in output
        assert "Rating" in output
        assert "Review" in output
        assert "Reviewer" in output
        assert "Replied" in output


class TestPrintReviewRow:
    def test_prints_review(self, capsys):
        review = _make_review()
        print_review_row(review)
        output = capsys.readouterr().out
        assert "2025-01-15" in output
        assert "Alice" in output

    def test_prints_replied_yes(self, capsys):
        review = _make_review(has_reply=True)
        print_review_row(review)
        output = capsys.readouterr().out
        assert "Yes" in output

    def test_prints_replied_no(self, capsys):
        review = _make_review(has_reply=False)
        print_review_row(review)
        output = capsys.readouterr().out
        assert "No" in output

    def test_multiline_comment_flattened(self, capsys):
        review = _make_review(comment="line1\nline2\nline3")
        print_review_row(review)
        output = capsys.readouterr().out
        assert "\n" not in output.strip()


class TestReadJsonlMetadata:
    def test_reads_ids_and_max_update_time(self, tmp_path):
        path = tmp_path / "reviews.jsonl"
        reviews = [
            {"review_id": "r1", "update_time": "2025-01-10T00:00:00+00:00"},
            {"review_id": "r2", "update_time": "2025-01-15T00:00:00+00:00"},
        ]
        path.write_text("\n".join(json.dumps(r) for r in reviews))

        ids, max_time = read_jsonl_metadata(path)
        assert ids == {"r1", "r2"}
        assert max_time == datetime(2025, 1, 15, tzinfo=timezone.utc)

    def test_skips_blank_lines(self, tmp_path):
        path = tmp_path / "reviews.jsonl"
        path.write_text('{"review_id": "r1", "update_time": "2025-01-10T00:00:00+00:00"}\n\n\n')

        ids, max_time = read_jsonl_metadata(path)
        assert ids == {"r1"}


class TestWriteReviewsJsonl:
    def test_writes_reviews(self, tmp_path):
        path = tmp_path / "reviews.jsonl"
        reviews = [_make_review(review_id="r1"), _make_review(review_id="r2")]
        write_reviews_jsonl(reviews, path)

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["review_id"] == "r1"
        assert json.loads(lines[1])["review_id"] == "r2"


class TestSyncReviewsJsonl:
    def _write_jsonl(self, path, reviews):
        with path.open("w") as f:
            for r in reviews:
                f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

    def test_appends_new_reviews(self, tmp_path):
        path = tmp_path / "reviews.jsonl"
        existing = [_make_review(review_id="r1")]
        self._write_jsonl(path, existing)

        new_review = _make_review(review_id="r2")
        new_count, updated_count = sync_reviews_jsonl([new_review], path, {"r1"})

        assert new_count == 1
        assert updated_count == 0
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_updates_existing_reviews(self, tmp_path):
        path = tmp_path / "reviews.jsonl"
        existing = [_make_review(review_id="r1", comment="old")]
        self._write_jsonl(path, existing)

        updated = _make_review(review_id="r1", comment="new")
        new_count, updated_count = sync_reviews_jsonl([updated], path, {"r1"})

        assert new_count == 0
        assert updated_count == 1
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0])["comment"] == "new"

    def test_mixed_new_and_updated(self, tmp_path):
        path = tmp_path / "reviews.jsonl"
        existing = [_make_review(review_id="r1", comment="old")]
        self._write_jsonl(path, existing)

        reviews = [
            _make_review(review_id="r1", comment="updated"),
            _make_review(review_id="r2", comment="brand new"),
        ]
        new_count, updated_count = sync_reviews_jsonl(reviews, path, {"r1"})

        assert new_count == 1
        assert updated_count == 1
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_no_changes(self, tmp_path):
        path = tmp_path / "reviews.jsonl"
        existing = [_make_review(review_id="r1")]
        self._write_jsonl(path, existing)

        new_count, updated_count = sync_reviews_jsonl([], path, {"r1"})
        assert new_count == 0
        assert updated_count == 0
