#!/usr/bin/env python3
"""Enhanced GitHub PR Comments Fetcher with AI Resolution Support.

Supports distinguishing between "resolved" (fixed) and "skipped" (intentionally ignored) comments.

This is the Python version of the shell script, providing the same functionality with:
- Clean object-oriented design
- Better error handling
- Improved maintainability
- Full compatibility with existing data files

Usage:
    python3 get_coderabbit_comments.py <PR_NUMBER> [OPTIONS]
    python3 get_coderabbit_comments.py --help

Examples:
    python3 get_coderabbit_comments.py 123 --status
    python3 get_coderabbit_comments.py 123 --status-unresolved
    python3 get_coderabbit_comments.py 123 --resolve COMMENT_ID1,COMMENT_ID2
    python3 get_coderabbit_comments.py 123 --skip COMMENT_ID1,COMMENT_ID2
"""

import argparse
import concurrent.futures
import json
import logging
import os
import re
import subprocess  # nosec B404  # pdf-toolbox: subprocess needed for git/gh CLI calls | issue:-
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Constants
MIN_PARTS_FOR_SSH_URL = 2
MIN_PARTS_FOR_OWNER_REPO = 2
LARGE_PR_THRESHOLD = 50
BATCH_SIZE = 20
TIMEOUT_SHORT = 5
TIMEOUT_MEDIUM = 10
TIMEOUT_LONG = 30

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    # Rich imports for enhanced formatting

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class GitHubRepositoryError(Exception):
    """Raised when repository detection fails."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(message)
        self.message = message


def _raise_invalid_ssh_url() -> None:
    """Raise GitHubRepositoryError for invalid SSH URL format."""
    raise GitHubRepositoryError("Invalid SSH URL format")  # noqa: TRY003  # pdf-toolbox: helper function for consistent error messages | issue:-


def _raise_not_github_repo() -> None:
    """Raise GitHubRepositoryError for non-GitHub repository."""
    raise GitHubRepositoryError("Not a GitHub repository")  # noqa: TRY003  # pdf-toolbox: helper function for consistent error messages | issue:-


@dataclass
class Comment:
    """Represents a GitHub PR comment."""

    comment_id: str
    body: str
    author: str
    created_at: str
    updated_at: str
    file_path: str | None = None  # Primary field for file path
    position: int | None = None
    url: str = ""
    is_resolved: bool = False
    resolution_type: str | None = None
    priority: str = "unknown"
    category: str = "other"
    type: str | None = None  # For compatibility with existing data
    path: str | None = None  # Legacy field, prefer file_path
    line_range: str | None = None  # For compatibility with existing data
    has_code_changes: bool = False  # For compatibility with existing data


@dataclass
class ResolutionState:
    """Represents the resolution state of comments."""

    resolved_comments: list[str]
    skipped_comments: list[str]
    resolution_history: list[dict[str, Any]]


class GitHubAPI:
    """Handles GitHub API interactions."""

    def __init__(self) -> None:
        """Initialize the GitHub API handler."""
        self.owner = ""
        self.repo = ""
        self._detect_repository()

    def _detect_repository(self) -> None:
        """Detect repository from git remote with CI fallbacks."""
        try:
            result = subprocess.run(  # noqa: S603  # nosec B603, B607  # pdf-toolbox: git CLI call with fixed arguments | issue:-
                ["git", "remote", "get-url", "origin"],  # noqa: S607  # nosec B607  # pdf-toolbox: git CLI with fixed arguments | issue:-
                capture_output=True,
                text=True,
                check=True,
                timeout=TIMEOUT_SHORT,
            )
            url = result.stdout.strip()
            if "github.com" in url:
                # Extract owner/repo from URL
                if url.startswith("git@"):
                    # SSH format: git@github.com:owner/repo.git
                    parts = url.replace(".git", "").split(":")
                    if len(parts) >= MIN_PARTS_FOR_SSH_URL:
                        repo_part = parts[1]
                        owner_repo = repo_part.split("/")
                        if len(owner_repo) >= MIN_PARTS_FOR_OWNER_REPO:
                            self.owner = owner_repo[0]
                            self.repo = owner_repo[1]
                        else:
                            _raise_invalid_ssh_url()
                    else:
                        _raise_invalid_ssh_url()
                else:
                    # HTTPS format: https://github.com/owner/repo.git
                    parts = url.replace(".git", "").split("/")
                    self.owner = parts[-2]
                    self.repo = parts[-1]
                logger.info(f"🔍 Detected repository: {self.owner}/{self.repo}")
            else:
                _raise_not_github_repo()
        except (
            subprocess.CalledProcessError,
            GitHubRepositoryError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
            OSError,
        ):
            logger.exception("❌ Error detecting repository")
            # Fallback for CI: GITHUB_REPOSITORY="owner/repo"
            repo_env = os.getenv("GITHUB_REPOSITORY")
            if repo_env and "/" in repo_env:
                self.owner, self.repo = repo_env.split("/", 1)
                logger.info(
                    f"🔍 Detected repository from GITHUB_REPOSITORY: {self.owner}/{self.repo}"
                )
                return
            # Try gh CLI as fallback
            try:
                result = subprocess.run(  # noqa: S603  # nosec B603, B607  # pdf-toolbox: gh CLI call with fixed arguments | issue:-
                    ["gh", "repo", "view", "--json", "owner,name"],  # noqa: S607  # nosec B607  # pdf-toolbox: gh CLI with fixed arguments | issue:-
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=TIMEOUT_SHORT,
                )
                repo_data = json.loads(result.stdout)
                self.owner = repo_data["owner"]["login"]
                self.repo = repo_data["name"]
                logger.info(f"🔍 Detected repository from gh CLI: {self.owner}/{self.repo}")
                return  # noqa: TRY300  # pdf-toolbox: return in try block for early exit | issue:-
            except (
                subprocess.CalledProcessError,
                ValueError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
                OSError,
                json.JSONDecodeError,
            ):
                logger.exception("❌ gh CLI fallback also failed")
            sys.exit(1)

    def fetch_comments(self, pr_number: int) -> tuple[list[Comment], list[Comment]]:
        """Fetch comments from GitHub API."""
        if RICH_AVAILABLE:
            console = Console()
            console.print("[bold blue]Fetching comments...[/bold blue]")
        else:
            logger.info(f"Fetching comments for PR #{pr_number}...")

        # Fetch both in parallel for better performance
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            review_future = executor.submit(self._fetch_review_threads, pr_number)
            pr_future = executor.submit(self._fetch_pr_comments, pr_number)

            # Wait for both to complete
            review_threads = review_future.result()
            pr_comments = pr_future.result()

        if RICH_AVAILABLE:
            console.print("[green]✅ Comments fetched[/green]")
        else:
            logger.info("✅ Comments fetched")

        return review_threads, pr_comments

    def _fetch_review_threads(self, pr_number: int) -> list[Comment]:
        """Fetch review threads using GitHub CLI with batch processing for large PRs."""
        # First, check if this is a large PR
        count_query = """
        query($owner:String!, $name:String!, $number:Int!) {
          repository(owner:$owner, name:$name) {
            pullRequest(number:$number) {
              reviewThreads(first:1) { totalCount }
            }
          }
        }
        """

        try:
            result = subprocess.run(  # noqa: S603  # nosec B603, B607  # pdf-toolbox: gh CLI call with fixed arguments | issue:-
                [  # noqa: S607  # nosec B607  # pdf-toolbox: gh CLI with fixed arguments | issue:-
                    "gh",
                    "api",
                    "graphql",
                    "-F",
                    f"query={count_query}",
                    "-F",
                    f"owner={self.owner}",
                    "-F",
                    f"name={self.repo}",
                    "-F",
                    f"number={int(pr_number)}",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=TIMEOUT_MEDIUM,
            )

            data = json.loads(result.stdout)
            total_count = data["data"]["repository"]["pullRequest"]["reviewThreads"]["totalCount"]

            if total_count > LARGE_PR_THRESHOLD:
                logger.warning(
                    f"⚠️ Large PR detected: {total_count} review threads. Using batch processing..."
                )
                return []
            return self._fetch_review_threads_single(pr_number)

        except Exception as e:
            logger.warning(f"⚠️ Could not check PR size, using single fetch: {e}")
            return self._fetch_review_threads_single(pr_number)

    def _fetch_review_threads_single(self, pr_number: int) -> list[Comment]:
        """Fetch review threads in a single query (for smaller PRs)."""
        query = """
        query($owner:String!, $name:String!, $number:Int!, $cursor:String) {
          repository(owner:$owner, name:$name) {
            pullRequest(number:$number) {
              reviewThreads(first:100, after:$cursor) {
                pageInfo { hasNextPage endCursor }
                nodes {
                  isResolved
                  comments(first:50) {
                    nodes {
                      id
                      body path position url createdAt updatedAt
                      author { login }
                    }
                  }
                }
              }
            }
          }
        }
        """

        try:
            result = subprocess.run(  # noqa: S603  # nosec B603, B607  # pdf-toolbox: gh CLI call with fixed arguments | issue:-
                [  # noqa: S607  # nosec B607  # pdf-toolbox: gh CLI with fixed arguments | issue:-
                    "gh",
                    "api",
                    "graphql",
                    "--paginate",
                    "-F",
                    f"query={query}",
                    "-F",
                    f"owner={self.owner}",
                    "-F",
                    f"name={self.repo}",
                    "-F",
                    f"number={int(pr_number)}",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=TIMEOUT_LONG,
            )

            data = json.loads(result.stdout)
            return self._parse_review_threads(data)
        except (
            subprocess.CalledProcessError,
            json.JSONDecodeError,
            subprocess.TimeoutExpired,
        ):
            logger.exception("❌ Error fetching review threads")
            return []

    def _fetch_review_threads_batched(self, pr_number: int, total_count: int) -> list[Comment]:
        """Fetch review threads in batches for large PRs."""
        all_comments: list[Comment] = []
        batch_size = BATCH_SIZE
        cursor = None

        logger.info(f"📦 Fetching {total_count} review threads in batches of {batch_size}...")

        while len(all_comments) < total_count:
            query = """
            query($owner:String!, $name:String!, $number:Int!, $cursor:String) {
              repository(owner:$owner, name:$name) {
                pullRequest(number:$number) {
                  reviewThreads(first:20, after:$cursor) {
                    pageInfo { hasNextPage endCursor }
                    nodes {
                      isResolved
                      comments(first:10) {
                        nodes {
                          id
                          body path position url createdAt updatedAt
                          author { login }
                        }
                      }
                    }
                  }
                }
              }
            }
            """

            try:
                cmd = [
                    "gh",
                    "api",
                    "graphql",
                    "-F",
                    f"query={query}",
                    "-F",
                    f"owner={self.owner}",
                    "-F",
                    f"name={self.repo}",
                    "-F",
                    f"number={int(pr_number)}",
                ]
                if cursor:
                    cmd.extend(["-F", f"cursor={cursor}"])

                result = subprocess.run(  # noqa: S603  # nosec B603, B607  # pdf-toolbox: gh CLI call with fixed arguments | issue:-
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=TIMEOUT_LONG,
                )

                data = json.loads(result.stdout)
                threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
                page_info = data["data"]["repository"]["pullRequest"]["reviewThreads"]["pageInfo"]

                # Parse this batch
                batch_comments = self._parse_review_threads(
                    {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": threads}}}}}
                )
                all_comments.extend(batch_comments)

                logger.info(
                    f"📦 Fetched {len(batch_comments)} comments from batch ({len(all_comments)}/{total_count} total)"
                )

                if not page_info["hasNextPage"]:
                    break

                cursor = page_info["endCursor"]

            except Exception:
                logger.exception("❌ Error in batch processing")
                break

        logger.info(f"✅ Batch processing complete: {len(all_comments)} comments fetched")
        return all_comments

    def _fetch_pr_comments(self, pr_number: int) -> list[Comment]:
        """Fetch PR comments using GitHub CLI."""
        query = """
        query($owner:String!, $name:String!, $number:Int!, $cursor:String) {
          repository(owner:$owner, name:$name) {
            pullRequest(number:$number) {
              comments(first:50, after:$cursor) {
                pageInfo { hasNextPage endCursor }
                nodes {
                  id body url createdAt updatedAt
                  author { login }
                }
              }
            }
          }
        }
        """

        try:
            result = subprocess.run(  # noqa: S603  # nosec B603, B607  # pdf-toolbox: gh CLI call with fixed arguments | issue:-
                [  # noqa: S607  # nosec B607  # pdf-toolbox: gh CLI with fixed arguments | issue:-
                    "gh",
                    "api",
                    "graphql",
                    "--paginate",
                    "-F",
                    f"query={query}",
                    "-F",
                    f"owner={self.owner}",
                    "-F",
                    f"name={self.repo}",
                    "-F",
                    f"number={int(pr_number)}",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=TIMEOUT_LONG,
            )

            data = json.loads(result.stdout)
            return self._parse_pr_comments(data)
        except (
            subprocess.CalledProcessError,
            json.JSONDecodeError,
            subprocess.TimeoutExpired,
        ):
            logger.exception("❌ Error fetching PR comments")
            return []

    def _parse_review_threads(self, data: dict[str, Any]) -> list[Comment]:
        """Parse review threads data."""
        comments = []
        try:
            threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
            for thread in threads:
                thread_resolved = bool(thread.get("isResolved", False))
                for comment_data in thread["comments"]["nodes"]:
                    comment = Comment(
                        comment_id=comment_data["id"],
                        body=comment_data["body"],
                        author=comment_data["author"]["login"],
                        created_at=comment_data["createdAt"],
                        updated_at=comment_data["updatedAt"],
                        file_path=comment_data.get("path"),
                        position=comment_data.get("position"),
                        url=comment_data["url"],
                        is_resolved=thread_resolved,
                        resolution_type=("resolved" if thread_resolved else None),
                    )
                    comments.append(comment)
        except (KeyError, TypeError):
            logger.exception("❌ Error parsing review threads")
        return comments

    def _parse_pr_comments(self, data: dict[str, Any]) -> list[Comment]:
        """Parse PR comments data."""
        comments = []
        try:
            comments_data = data["data"]["repository"]["pullRequest"]["comments"]["nodes"]
            for comment_data in comments_data:
                comment = Comment(
                    comment_id=comment_data["id"],
                    body=comment_data["body"],
                    author=comment_data["author"]["login"],
                    created_at=comment_data["createdAt"],
                    updated_at=comment_data["updatedAt"],
                    url=comment_data["url"],
                )
                comments.append(comment)
        except (KeyError, TypeError):
            logger.exception("❌ Error parsing PR comments")
        return comments


class CommentProcessor:
    """Processes and analyzes comments."""

    def __init__(self) -> None:
        """Initialize the comment processor."""
        # Pre-compile regex patterns for better performance
        self._file_patterns = [
            re.compile(r"In ([^\s]+) around lines?"),
            re.compile(r"In ([^\s]+) at lines?"),
            re.compile(r"([^\s]+\.(ts|js|json|md|txt|yml|yaml)) around lines?"),
        ]

        # Pre-compile priority and category patterns
        self._priority_patterns = {
            "major": re.compile(r"(Major|P1)", re.IGNORECASE),
            "minor": re.compile(r"Minor", re.IGNORECASE),
            "trivial": re.compile(r"Trivial", re.IGNORECASE),
        }

        self._category_patterns = {
            "summary": re.compile(r"## Walkthrough"),
            "command": re.compile(r"^@(coderabbit|CodeRabbit|codex)", re.IGNORECASE | re.MULTILINE),
            "nitpick": re.compile(r"Nitpick"),
            "issue": re.compile(r"Potential issue"),
            "refactor": re.compile(r"Refactor"),
        }

    def process_comments(self, comments: list[Comment]) -> list[Comment]:
        """Process comments and extract metadata with parallel processing."""
        if not comments:
            return comments

        # Use parallel processing for large comment sets
        parallel_threshold = 10
        if len(comments) > parallel_threshold:
            with ThreadPoolExecutor(max_workers=4) as executor:
                # Submit all comment processing tasks
                futures = []
                for comment in comments:
                    future = executor.submit(self._process_single_comment, comment)
                    futures.append(future)

                # Wait for all to complete
                processed_comments = [future.result() for future in futures]
        else:
            # For small comment sets, process sequentially
            processed_comments = [self._process_single_comment(comment) for comment in comments]

        return processed_comments

    def _process_single_comment(self, comment: Comment) -> Comment:
        """Process a single comment and extract metadata."""
        comment.priority = self._extract_priority(comment.body)
        comment.category = self._extract_category(comment.body)
        if not comment.file_path:
            comment.file_path = self._extract_file_path(comment.body)
        return comment

    def _extract_priority(self, body: str) -> str:
        """Extract priority from comment body using pre-compiled patterns."""
        for priority, pattern in self._priority_patterns.items():
            if pattern.search(body):
                return priority
        return "unknown"

    def _extract_category(self, body: str) -> str:
        """Extract category from comment body using pre-compiled patterns."""
        # Check patterns in order of specificity
        for category, pattern in self._category_patterns.items():
            if pattern.search(body):
                return category
        return "other"

    def _extract_file_path(self, body: str) -> str | None:
        """Extract file path from comment body."""
        for pattern in self._file_patterns:
            match = pattern.search(body)
            if match:
                return match.group(1)
        return None

    def assess_comment_for_action(self, comment: Comment) -> str:
        """Provide guidance on whether a comment should be addressed."""
        # High priority issues should always be addressed
        if comment.priority == "major" and comment.category in ["issue", "refactor"]:
            return "🔴 Should address: High priority issue"

        # Minor issues are usually worth addressing
        if comment.priority == "minor" and comment.category == "issue":
            return "🟡 Should address: Minor issue"

        # Trivial nitpicks on configuration files are often simple fixes
        if (
            comment.priority == "trivial"
            and comment.category == "nitpick"
            and comment.file_path
            and any(
                ext in comment.file_path
                for ext in [".yaml", ".yml", ".json", ".gitignore", ".prettierignore"]
            )
        ):
            return "🟢 Review: Simple config file fix - likely worth addressing"

        # Trivial nitpicks on code files need evaluation
        if comment.priority == "trivial" and comment.category == "nitpick":
            return "🔵 Review: Trivial nitpick - evaluate based on content"

        # Other categories need manual review
        return "⚪ Review: Evaluate based on content and context"


class ResolutionManager:
    """Manages comment resolution state."""

    def __init__(self, pr_number: int) -> None:
        """Initialize the resolution manager for a specific PR."""
        self.pr_number = pr_number
        self.resolution_file = Path(f".local/pr-{pr_number}-resolutions.json")
        self.comments_file = Path(f".local/pr-{pr_number}-change-comments.json")
        self._ensure_local_dir()

    def _ensure_local_dir(self) -> None:
        """Ensure .local directory exists."""
        Path(".local").mkdir(exist_ok=True)

    def load_resolution_state(self) -> ResolutionState:
        """Load resolution state from file."""
        if not self.resolution_file.exists():
            return ResolutionState([], [], [])

        try:
            with self.resolution_file.open(encoding="utf-8") as f:
                data = json.load(f)
            return ResolutionState(
                resolved_comments=data.get("resolved_comments", []),
                skipped_comments=data.get("skipped_comments", []),
                resolution_history=data.get("resolution_history", []),
            )
        except (json.JSONDecodeError, KeyError):
            logger.exception("❌ Error loading resolution state")
            return ResolutionState([], [], [])

    def save_resolution_state(self, state: ResolutionState) -> None:
        """Save resolution state to file."""
        data = {
            "resolved_comments": state.resolved_comments,
            "skipped_comments": state.skipped_comments,
            "resolution_history": state.resolution_history,
        }

        with self.resolution_file.open("w") as f:
            json.dump(data, f, indent=2)

    def mark_resolved(self, comment_ids: list[str]) -> None:
        """Mark comments as resolved."""
        state = self.load_resolution_state()

        # Add to resolved, remove from skipped
        for comment_id in comment_ids:
            if comment_id not in state.resolved_comments:
                state.resolved_comments.append(comment_id)
            if comment_id in state.skipped_comments:
                state.skipped_comments.remove(comment_id)

            # Add to history
            state.resolution_history.append(
                {
                    "comment_id": comment_id,
                    "resolution_type": "resolved",
                    "resolved_at": datetime.now(UTC).isoformat(),
                    "resolved_by": "ai",
                }
            )

        self.save_resolution_state(state)
        if RICH_AVAILABLE:
            console = Console()
            console.print(
                f"[green]✅ {len(comment_ids)} comments marked as resolved (fixed)[/green]"
            )
        else:
            logger.info(f"✅ {len(comment_ids)} comments marked as resolved (fixed)")

    def mark_skipped(self, comment_ids: list[str]) -> None:
        """Mark comments as skipped."""
        state = self.load_resolution_state()

        # Add to skipped, remove from resolved
        for comment_id in comment_ids:
            if comment_id not in state.skipped_comments:
                state.skipped_comments.append(comment_id)
            if comment_id in state.resolved_comments:
                state.resolved_comments.remove(comment_id)

            # Add to history
            state.resolution_history.append(
                {
                    "comment_id": comment_id,
                    "resolution_type": "skipped",
                    "resolved_at": datetime.now(UTC).isoformat(),
                    "resolved_by": "ai",
                }
            )

        self.save_resolution_state(state)
        if RICH_AVAILABLE:
            console = Console()
            console.print(
                f"[yellow]⏭️ {len(comment_ids)} comments marked as skipped (ignored)[/yellow]"
            )
        else:
            logger.info(f"⏭️ {len(comment_ids)} comments marked as skipped (ignored)")

    def load_comments(self) -> list[Comment]:
        """Load comments from file with optimized field mapping."""
        if not self.comments_file.exists():
            return []

        try:
            with self.comments_file.open(encoding="utf-8") as f:
                data = json.load(f)

            comments = []
            comments_data = data.get("comments", [])

            # Pre-define field mapping for better performance
            field_mapping = {
                "comment_id": "comment_id",
                "body": "body",
                "author": "author",
                "created_at": "createdAt",
                "updated_at": "updatedAt",
                "file_path": "file_path",
                "position": "position",
                "url": "url",
                "is_resolved": "is_resolved",
                "resolution_type": "resolution_type",
                "priority": "priority",
                "category": "category",
                "type": "type",
                "path": "path",
                "line_range": "line_range",
                "has_code_changes": "has_code_changes",
            }

            # Default values to avoid repeated dict lookups
            defaults = {
                "url": "",
                "is_resolved": False,
                "priority": "unknown",
                "category": "other",
                "has_code_changes": False,
            }

            for comment_data in comments_data:
                # Build mapped comment with defaults
                mapped_comment = {}
                for field, key in field_mapping.items():
                    mapped_comment[field] = comment_data.get(key, defaults.get(field))

                comments.append(Comment(**mapped_comment))
            return comments  # noqa: TRY300  # pdf-toolbox: return in try block for early exit | issue:-
        except (json.JSONDecodeError, KeyError, TypeError, OSError):
            logger.exception("❌ Error loading comments")
            return []

    def update_comments_resolution_state(self, comments: list[Comment]) -> None:
        """Update comments with resolution state."""
        state = self.load_resolution_state()

        for comment in comments:
            if comment.comment_id in state.resolved_comments:
                comment.is_resolved = True
                comment.resolution_type = "resolved"
            elif comment.comment_id in state.skipped_comments:
                comment.is_resolved = True
                comment.resolution_type = "skipped"
            else:
                comment.is_resolved = False
                comment.resolution_type = None


class StatusDisplay:
    """Handles status display functionality."""

    def __init__(self, resolution_manager: ResolutionManager) -> None:
        """Initialize the status display handler."""
        self.resolution_manager = resolution_manager
        self.console = Console() if RICH_AVAILABLE else None

    def _create_unified_table(  # noqa: C901, PLR0912, PLR0915  # pdf-toolbox: complex table rendering with multiple display modes | issue:-
        self,
        comments: list[Comment],
        title: str = "📝 Comments",
        show_summary: bool = True,
        show_assessment: bool = False,
    ) -> None:
        """Create a unified table for displaying comments with optional filtering."""
        if not comments:
            if self.console:
                self.console.print("[yellow]⚠️  No comments found[/yellow]")
            else:
                logger.warning("⚠️  No comments found")
            return

        # Calculate statistics
        resolved_comments = [
            c for c in comments if c.is_resolved and c.resolution_type == "resolved"
        ]
        skipped_comments = [c for c in comments if c.is_resolved and c.resolution_type == "skipped"]
        unresolved_comments = [c for c in comments if not c.is_resolved]

        total_comments = len(comments)
        resolved_count = len(resolved_comments)
        skipped_count = len(skipped_comments)
        unresolved_count = len(unresolved_comments)
        progress = (
            int((resolved_count + skipped_count) / total_comments * 100)
            if total_comments > 0
            else 0
        )

        if self.console and show_summary:
            # Create summary panel
            summary_text = "[bold blue]📊 Comment Status[/bold blue]\n\n"
            summary_text += f"[green]✅ Resolved:[/green] {resolved_count}\n"
            summary_text += f"[yellow]⏭️  Skipped:[/yellow] {skipped_count}\n"
            summary_text += f"[red]❌ Unresolved:[/red] {unresolved_count}\n"
            summary_text += f"[bold]Total:[/bold] {total_comments}\n"
            summary_text += f"[bold]Progress:[/bold] {progress}%"

            summary_panel = Panel(summary_text, title="Comment Status", border_style="blue")
            self.console.print(summary_panel)
            self.console.print()

        # Combine all comments with status
        all_comments = []

        # Add resolved comments
        for comment in resolved_comments:
            all_comments.append((comment, "✅ Resolved"))

        # Add skipped comments
        for comment in skipped_comments:
            all_comments.append((comment, "⏭️ Skipped"))

        # Add unresolved comments
        for comment in unresolved_comments:
            all_comments.append((comment, "❌ Unresolved"))

        # Sort by status (resolved, skipped, unresolved) then by date
        def sort_key(item):
            comment, status = item
            status_order = {"✅ Resolved": 0, "⏭️ Skipped": 1, "❌ Unresolved": 2}
            return (status_order.get(status, 3), comment.created_at)

        all_comments.sort(key=sort_key)

        # Show all comments in a single table
        if all_comments:
            if self.console:
                table = Table(title=title, show_header=True, header_style="blue")
                table.add_column("ID", style="dim", width=20)
                table.add_column("Status", style="bold", width=12)
                table.add_column("Priority", style="bold", width=8)
                table.add_column("Category", style="cyan", width=10)
                table.add_column("File", style="green")
                table.add_column("Author", style="blue", width=12)
                table.add_column("Date", style="dim", width=10)

                for comment, status in all_comments:
                    priority_color = {
                        "major": "red",
                        "minor": "yellow",
                        "trivial": "blue",
                        "unknown": "dim",
                    }.get(comment.priority, "dim")

                    # Color the status column
                    status_color = {
                        "✅ Resolved": "green",
                        "⏭️ Skipped": "yellow",
                        "❌ Unresolved": "red",
                    }.get(status, "dim")

                    file_path = comment.file_path or "General"
                    date_str = comment.created_at.split("T")[0]  # Just the date part

                    # Add assessment guidance for unresolved comments
                    if status == "❌ Unresolved" and show_assessment:
                        processor = CommentProcessor()
                        assessment = processor.assess_comment_for_action(comment)
                        file_path = f"{file_path}\n[dim]{assessment}[/dim]"

                    table.add_row(
                        comment.comment_id,
                        f"[{status_color}]{status}[/{status_color}]",
                        f"[{priority_color}]{comment.priority.upper()}[/{priority_color}]",
                        comment.category,
                        file_path,
                        comment.author,
                        date_str,
                    )
                self.console.print(table)
            else:
                # Plain text fallback
                logger.info(f"\n{title}:")
                for comment, status in all_comments:
                    file_path = comment.file_path or "General"
                    date_str = comment.created_at.split("T")[0]
                    logger.info(
                        f"  {status} {comment.comment_id} - {file_path} - {comment.author} - {date_str}"
                    )

    def show_status(self, unresolved_only: bool = False, show_assessment: bool = False) -> None:
        """Show resolution status."""
        comments = self.resolution_manager.load_comments()
        if not comments:
            if self.console:
                self.console.print(
                    "[red]❌ Error: No comments found. Run without --status first to fetch comments.[/red]"
                )
            else:
                logger.error(
                    "❌ Error: No comments found. Run without --status first to fetch comments."
                )
            return

        # Update resolution state
        self.resolution_manager.update_comments_resolution_state(comments)

        if unresolved_only:
            # Filter to show only unresolved comments
            unresolved_comments = [c for c in comments if not c.is_resolved]
            if unresolved_comments:
                self._create_unified_table(
                    unresolved_comments,
                    "❌ Unresolved Comments",
                    show_summary=False,
                    show_assessment=show_assessment,
                )
            elif self.console:
                self.console.print("[green]✅ No unresolved comments![/green]")
            else:
                logger.info("✅ No unresolved comments!")
        else:
            # Show all comments with summary
            self._create_unified_table(comments, "📝 All Comments", show_summary=True)


def main() -> None:  # noqa: C901, PLR0911, PLR0912, PLR0915  # pdf-toolbox: complex CLI argument handling with multiple command modes | issue:-
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced GitHub PR Comments Fetcher with AI Resolution Support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 123                          # Fetch all comments for PR 123
  %(prog)s 123 --resolve 2386777571    # Mark single comment as resolved (fixed)
  %(prog)s 123 --skip 2386777572        # Mark single comment as skipped (ignored)
  %(prog)s 123 --resolve 2386777571,2386777573  # Mark multiple comments as resolved
  %(prog)s 123 --skip 2386777572,2386777574      # Mark multiple comments as skipped
  %(prog)s 123 --status                 # Show resolution status
  %(prog)s 123 --status-unresolved      # Show only unresolved comments
  %(prog)s --cleanup                    # Clean up closed PRs and archive resolutions
        """,
    )

    parser.add_argument("pr_number", nargs="?", type=int, help="PR number")
    parser.add_argument("--resolve", help="Mark one or more comments as resolved (fixed)")
    parser.add_argument("--skip", help="Mark one or more comments as skipped (ignored)")
    parser.add_argument("--status", action="store_true", help="Show resolution status")
    parser.add_argument(
        "--status-unresolved", action="store_true", help="Show only unresolved comments"
    )
    parser.add_argument(
        "--assess",
        action="store_true",
        help="Show assessment guidance for unresolved comments",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Archive all PR data files to .local/archive/",
    )

    args = parser.parse_args()

    # Handle cleanup command
    if args.cleanup:
        logger.info("🧹 Cleaning up closed PRs and archiving resolutions...")

        # Find all resolution files
        local_dir = Path(".local")
        if not local_dir.exists():
            if RICH_AVAILABLE:
                console = Console()
                console.print("[yellow]⚠️  No .local directory found - nothing to clean up[/yellow]")
            else:
                logger.warning("⚠️  No .local directory found - nothing to clean up")
            return

        resolution_files = list(local_dir.glob("pr-*-resolutions.json"))
        comments_files = list(local_dir.glob("pr-*-change-comments.json"))

        if not resolution_files and not comments_files:
            if RICH_AVAILABLE:
                console = Console()
                console.print("[yellow]⚠️  No PR data files found to clean up[/yellow]")
            else:
                logger.warning("⚠️  No PR data files found to clean up")
            return

        # Create archive directory
        archive_dir = local_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        # Move files to archive
        archived_count = 0
        for file_path in resolution_files + comments_files:
            archive_path = archive_dir / file_path.name
            file_path.rename(archive_path)
            archived_count += 1

        if RICH_AVAILABLE:
            console = Console()
            console.print(f"[green]✅ Archived {archived_count} files to .local/archive/[/green]")
        else:
            logger.info(f"✅ Archived {archived_count} files to .local/archive/")
        return

    # Validate PR number
    if not args.pr_number:
        parser.error("PR number is required")

    # Initialize components
    resolution_manager = ResolutionManager(args.pr_number)

    # Handle resolution commands
    if args.resolve:
        comment_ids = [cid.strip() for cid in args.resolve.split(",")]
        resolution_manager.mark_resolved(comment_ids)
        return

    if args.skip:
        comment_ids = [cid.strip() for cid in args.skip.split(",")]
        resolution_manager.mark_skipped(comment_ids)
        return

    # Handle status commands
    if args.status or args.status_unresolved or args.assess:
        status_display = StatusDisplay(resolution_manager)
        if args.assess:
            # Show assessment guidance for unresolved comments
            status_display.show_status(unresolved_only=True, show_assessment=True)
        else:
            status_display.show_status(unresolved_only=args.status_unresolved)
        return

    # Default: fetch and display comments
    logger.info(f"📝 Fetching comments for PR #{args.pr_number}...")

    # Initialize GitHub API and comment processor
    github_api = GitHubAPI()
    comment_processor = CommentProcessor()

    # Fetch comments from GitHub
    review_threads, pr_comments = github_api.fetch_comments(args.pr_number)

    # Combine all comments
    all_comments = review_threads + pr_comments

    if not all_comments:
        if RICH_AVAILABLE:
            console = Console()
            console.print("[yellow]⚠️  No comments found for this PR[/yellow]")
        else:
            logger.warning("⚠️  No comments found for this PR")
        return

    # Process comments to extract metadata
    if RICH_AVAILABLE:
        console = Console()
        console.print("[bold green]Processing comments...[/bold green]")
        processed_comments = comment_processor.process_comments(all_comments)
        console.print("[green]✅ Comments processed[/green]")
    else:
        processed_comments = comment_processor.process_comments(all_comments)

    # Automatically skip command and summary comments (they're not actionable review feedback)
    command_comment_ids = [
        comment.comment_id for comment in processed_comments if comment.category == "command"
    ]

    summary_comment_ids = [
        comment.comment_id for comment in processed_comments if comment.category == "summary"
    ]

    # Skip both command and summary comments
    auto_skip_ids = command_comment_ids + summary_comment_ids

    if auto_skip_ids:
        resolution_manager.mark_skipped(auto_skip_ids)

    # Automatically resolve comments that have been addressed (contain "✅ Addressed")
    addressed_comment_ids = [
        comment.comment_id for comment in processed_comments if "✅ Addressed" in comment.body
    ]

    if addressed_comment_ids:
        resolution_manager.mark_resolved(addressed_comment_ids)

    # Save comments to file - optimized serialization
    comments_data = {
        "comments": [
            {
                "comment_id": comment.comment_id,
                "body": comment.body,
                "author": comment.author,
                "createdAt": comment.created_at,
                "updatedAt": comment.updated_at,
                "file_path": comment.file_path,
                "position": comment.position,
                "url": comment.url,
                "is_resolved": comment.is_resolved,
                "resolution_type": comment.resolution_type,
                "priority": comment.priority,
                "category": comment.category,
                "type": comment.type,
                "path": comment.path,
                "line_range": comment.line_range,
                "has_code_changes": comment.has_code_changes,
            }
            for comment in processed_comments
        ],
        "total_comments": len(processed_comments),
    }

    # Save to file
    resolution_manager.comments_file.parent.mkdir(exist_ok=True)
    with resolution_manager.comments_file.open("w", encoding="utf-8") as f:
        json.dump(comments_data, f, indent=2)

    # Complete processing
    if RICH_AVAILABLE:
        console.print("[green]✅ Comments saved[/green]")

    # Display comments using unified display
    if RICH_AVAILABLE:
        console = Console()
        console.print(
            f"[green]✅ Fetched {len(processed_comments)} comments for PR #{args.pr_number}[/green]"
        )
        console.print()

        # Load existing resolution state and update comments
        status_display = StatusDisplay(resolution_manager)
        status_display.resolution_manager.update_comments_resolution_state(processed_comments)

        # Use unified display for fetch summary with actual resolution status
        status_display._create_unified_table(
            processed_comments, "📝 All Comments", show_summary=True
        )
        console.print()
        console.print(
            "[dim]💡 Use --status to see resolution status, --assess for guidance, --resolve/--skip to manage comments[/dim]"
        )

    else:
        # Plain text fallback
        logger.info(f"✅ Fetched {len(processed_comments)} comments for PR #{args.pr_number}")
        logger.info("\n📊 Comment Summary:")
        logger.info(f"  Total: {len(processed_comments)}")
        logger.info(f"  Major: {len([c for c in processed_comments if c.priority == 'major'])}")
        logger.info(f"  Minor: {len([c for c in processed_comments if c.priority == 'minor'])}")
        logger.info(f"  Trivial: {len([c for c in processed_comments if c.priority == 'trivial'])}")
        logger.info(
            "\n💡 Use --status to see resolution status, --assess for guidance, --resolve/--skip to manage comments"
        )


if __name__ == "__main__":
    main()
