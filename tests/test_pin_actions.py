"""Tests for normalising GitHub Actions pinning comments."""

from __future__ import annotations

import pytest

from scripts.pin_actions import normalise_uses_line


@pytest.mark.parametrize(
    "line,commit_sha,comment_label,published,expected",
    [
        (
            "- uses: actions/cache@v3  # pinned: actions/cache@v2 (2023-01-01)  # pinned: actions/cache@v3 (2024-02-01)  # note: keep 3.13",
            "0123456789abcdef0123456789abcdef01234567",
            "actions/cache@v3",
            "2024-02-01",
            "- uses: actions/cache@0123456789abcdef0123456789abcdef01234567  # pinned: actions/cache@v3 (2024-02-01)  # note: keep 3.13",
        ),
    ],
)
def test_preserves_manual_comments_and_single_pinned(
    line: str,
    commit_sha: str,
    comment_label: str,
    published: str,
    expected: str,
) -> None:
    """Ensure duplicate pinned entries collapse while manual comments stay."""

    assert (
        normalise_uses_line(
            line,
            commit_sha=commit_sha,
            comment_label=comment_label,
            published_date=published,
        )
        == expected
    )


def test_normalise_is_idempotent() -> None:
    """Running the normaliser twice should not change the line further."""

    line = "- uses: actions/setup-python@v5  # pinned: actions/setup-python@v4 (2023-01-01)  # note"
    first = normalise_uses_line(
        line,
        commit_sha="fedcba9876543210fedcba9876543210fedcba98",
        comment_label="actions/setup-python@v5",
        published_date="2024-01-10",
    )
    second = normalise_uses_line(
        first,
        commit_sha="fedcba9876543210fedcba9876543210fedcba98",
        comment_label="actions/setup-python@v5",
        published_date="2024-01-10",
    )
    assert second == first


def test_adds_pinned_comment_when_missing() -> None:
    """Lines without existing comments gain a pinned annotation."""

    line = "  uses: owner/action@v1"
    expected = (
        "  uses: owner/action@abcdefabcdefabcdefabcdefabcdefabcdef  "
        "# pinned: owner/action@v1 (2024-03-02)"
    )
    assert (
        normalise_uses_line(
            line,
            commit_sha="abcdefabcdefabcdefabcdefabcdefabcdef",
            comment_label="owner/action@v1",
            published_date="2024-03-02",
        )
        == expected
    )


def test_deduplicates_manual_comments_preserving_order() -> None:
    """Manual comments are deduplicated while keeping their original order."""

    line = (
        "- uses: owner/action@v1  # keep  # keep  # foo  # pinned: owner/action@v0 (2023-01-01)  # foo"
    )
    expected = (
        "- uses: owner/action@1234567890abcdef1234567890abcdef12345678  "
        "# pinned: owner/action@v1 (2024-04-05)  # keep  # foo"
    )
    assert (
        normalise_uses_line(
            line,
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            comment_label="owner/action@v1",
            published_date="2024-04-05",
        )
        == expected
    )


def test_handles_subpath_repositories() -> None:
    """Subpath references keep the full path while normalising comments."""

    line = "- uses: owner/action/sub/path@v2  # note"
    expected = (
        "- uses: owner/action/sub/path@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  "
        "# pinned: owner/action@v2 (2024-05-06)  # note"
    )
    assert (
        normalise_uses_line(
            line,
            commit_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            comment_label="owner/action@v2",
            published_date="2024-05-06",
        )
        == expected
    )


def test_non_uses_lines_are_untouched() -> None:
    """Only ``uses`` lines are rewritten."""

    line = "  run: echo 'uses: owner/action@v1'  # pinned: should stay"
    assert (
        normalise_uses_line(
            line,
            commit_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            comment_label="owner/action@v1",
            published_date="2024-07-08",
        )
        == line
    )


def test_tagged_inputs_normalise_to_sha() -> None:
    """Tagged inputs are rewritten to SHAs while referencing the tag in comments."""

    line = "- uses: owner/action@v9"
    expected = (
        "- uses: owner/action@cccccccccccccccccccccccccccccccccccccccc  "
        "# pinned: owner/action@v9 (2024-08-09)"
    )
    assert (
        normalise_uses_line(
            line,
            commit_sha="cccccccccccccccccccccccccccccccccccccccc",
            comment_label="owner/action@v9",
            published_date="2024-08-09",
        )
        == expected
    )
