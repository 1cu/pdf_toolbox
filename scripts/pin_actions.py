"""Pin GitHub Actions in workflow files to the latest stable release SHAs."""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import os
import re
import ssl
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib import error, parse, request

from pdf_toolbox.utils import logger as _project_logger

logger = _project_logger.getChild("scripts.pin_actions")

WORKFLOW_DIR = Path(".github/workflows")
USES_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?P<dash>-\s+)?uses:\s*(?P<quote>['\"]?)(?P<value>[^'\"#]+?)(?P=quote)\s*(?P<comment>#.*)?$"
)
PIN_COMMENT_PREFIX = "# pinned:"
MIN_REPO_SEGMENTS = 2
REQUEST_TIMEOUT_SECONDS = 10
PINNED_COMMENT_PATTERN = re.compile(r"(?i)^pinned:\s*")
COMMENT_TOKEN_PATTERN = re.compile(r"#([^#]*)")


def _deduplicate(tokens: Iterable[str]) -> list[str]:
    """Return tokens in first-seen order without duplicates.

    Args:
        tokens: Iterable of comment fragments to deduplicate.

    Returns:
        A list preserving the first occurrence of each token.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def extract_manual_comments(comment_blob: str) -> list[str]:
    """Split a trailing comment blob into manual comments without pinned entries.

    Args:
        comment_blob: Raw trailing comment text captured from a workflow line.

    Returns:
        Manual comment tokens (excluding ``pinned`` markers) without duplicates.
    """
    if not comment_blob:
        return []
    tokens = [
        match.group(1).strip() for match in COMMENT_TOKEN_PATTERN.finditer(comment_blob)
    ]
    manuals = [
        token for token in tokens if token and not PINNED_COMMENT_PATTERN.match(token)
    ]
    return _deduplicate(manuals)


def normalise_uses_line(
    line: str,
    *,
    commit_sha: str,
    comment_label: str,
    published_date: str,
) -> str:
    """Return a normalised ``uses`` line with a single pinned comment.

    Args:
        line: The original workflow line.
        commit_sha: The resolved commit SHA for the action reference.
        comment_label: The version text to include in the ``pinned`` comment.
        published_date: The publication date for the resolved ref.

    Returns:
        The updated line with the new SHA and deduplicated inline comments.
    """
    match = USES_PATTERN.match(line)
    if not match:
        return line
    if not match.group("dash") and not line.lstrip().startswith("uses:"):
        return line

    value = match.group("value").strip()
    if "@" not in value:
        return line
    action_path, _ = value.split("@", 1)

    manual_comments = extract_manual_comments(match.group("comment") or "")
    prefix = f"{match.group('indent') or ''}{match.group('dash') or ''}uses: "
    quote = match.group("quote") or ""
    pinned_comment = f"{PIN_COMMENT_PREFIX} {comment_label} ({published_date})"
    comment_suffix = ""
    if manual_comments:
        manual_suffix = "  ".join(f"# {token}" for token in manual_comments)
        comment_suffix = f"  {pinned_comment}  {manual_suffix}"
    else:
        comment_suffix = f"  {pinned_comment}"

    return f"{prefix}{quote}{action_path}@{commit_sha}{quote}{comment_suffix}"


class GitHubAPI:
    """Minimal helper for GitHub REST API requests."""

    def __init__(self, token: str | None) -> None:
        """Initialise the client with optional token-based authentication."""
        self._base_url = "https://api.github.com"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "pdf-toolbox-action-pinner",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._headers = headers
        fallback_cafile = Path("/etc/ssl/certs/ca-certificates.crt")
        if fallback_cafile.exists():
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            try:
                context.load_verify_locations(cafile=str(fallback_cafile))
            except ssl.SSLError:
                context = ssl.create_default_context()
        else:
            context = ssl.create_default_context()
        self._context = context

    def get(self, path: str, *, params: dict[str, str] | None = None) -> dict:
        """Execute a GET request and return the parsed JSON payload."""
        url = f"{self._base_url}{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"
        scheme = parse.urlsplit(url).scheme
        if scheme != "https":
            message = f"Unsupported URL scheme for GitHub API: {scheme}"
            raise ValueError(message)
        req = request.Request(  # noqa: S310  # pdf-toolbox: validated HTTPS request to GitHub API | issue:-
            url, headers=self._headers
        )
        try:
            with request.urlopen(  # noqa: S310 - GitHub API client  # nosec B310  # pdf-toolbox: GitHub API requests rely on urllib with pinned CA bundle | issue:-
                req, context=self._context, timeout=REQUEST_TIMEOUT_SECONDS
            ) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload)
        except error.HTTPError as exc:  # pragma: no cover - network failures are rare  # pdf-toolbox: log and rethrow network errors for diagnostics | issue:-
            message = exc.read().decode("utf-8", errors="ignore")
            error_message = f"GitHub API request failed for {url}: {exc}\n{message}"
            raise RuntimeError(error_message) from exc


@dataclass
class ActionOccurrence:
    """Occurrence of a third-party action reference in a workflow."""

    path: Path
    line_index: int
    leading: str
    quote: str
    repo: str
    subpath: str
    previous_ref: str
    trailing_comment: str


@dataclass
class ActionResolution:
    """Pinned resolution metadata for an action repository."""

    repo: str
    previous_refs: list[str]
    commit_sha: str
    comment_label: str
    published_date: str
    display_tag: str
    release_url: str
    note: str | None = None


def iter_workflow_files() -> Iterable[Path]:
    """Return workflow files sorted by path for deterministic processing."""
    if not WORKFLOW_DIR.exists():
        return []
    files: set[Path] = set()
    for pattern in ("**/*.yml", "**/*.yaml"):
        files.update(path for path in WORKFLOW_DIR.glob(pattern) if path.is_file())
    return sorted(files)


def parse_uses_lines(path: Path) -> list[ActionOccurrence]:
    """Extract action usages from a workflow file."""
    occurrences: list[ActionOccurrence] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines):
        match = USES_PATTERN.match(line)
        if not match:
            continue
        value = match.group("value").strip()
        if not value or "${{" in value:
            continue
        if value.startswith("./") or value.startswith(".github/"):
            continue
        if value.startswith("docker://"):
            continue
        if "@" not in value:
            continue
        action_path, previous_ref = value.split("@", 1)
        action_path = action_path.strip()
        previous_ref = previous_ref.strip()
        if not action_path or not previous_ref:
            continue
        segments = action_path.split("/")
        if len(segments) < MIN_REPO_SEGMENTS:
            continue
        repo = "/".join(segments[:2])
        subpath = "/".join(segments[2:])
        occurrences.append(
            ActionOccurrence(
                path=path,
                line_index=idx,
                leading=(match.group("indent") or "") + (match.group("dash") or ""),
                quote=match.group("quote") or "",
                repo=repo,
                subpath=subpath,
                previous_ref=previous_ref,
                trailing_comment=match.group("comment") or "",
            )
        )
    return occurrences


def collect_occurrences(files: Iterable[Path]) -> dict[str, list[ActionOccurrence]]:
    """Group action occurrences by repository."""
    action_map: dict[str, list[ActionOccurrence]] = {}
    for path in files:
        for occurrence in parse_uses_lines(path):
            action_map.setdefault(occurrence.repo, []).append(occurrence)
    return action_map


def iso_date(date_str: str) -> str:
    """Convert an ISO timestamp to YYYY-MM-DD."""
    timestamp = date_str
    if timestamp.endswith("Z"):
        timestamp = f"{timestamp[:-1]}+00:00"
    parsed = dt.datetime.fromisoformat(timestamp)
    return parsed.date().isoformat()


def resolve_tag_to_commit(api: GitHubAPI, owner: str, repo: str, tag: str) -> str:
    """Return the commit SHA for the given annotated or lightweight tag."""
    encoded_tag = parse.quote(tag, safe="")
    data = api.get(f"/repos/{owner}/{repo}/git/refs/tags/{encoded_tag}")
    ref_obj: dict | None
    if isinstance(data, list):
        ref_obj = next(
            (item for item in data if item.get("ref") == f"refs/tags/{tag}"), None
        )
        if ref_obj is None:
            message = f"Unable to resolve tag {tag} for {owner}/{repo}"
            raise RuntimeError(message)
    else:
        ref_obj = data
    obj = ref_obj["object"]
    if obj["type"] == "tag":
        tag_data = api.get(f"/repos/{owner}/{repo}/git/tags/{obj['sha']}")
        return tag_data["object"]["sha"]
    if obj["type"] == "commit":
        return obj["sha"]
    message = f"Unsupported tag object type {obj['type']} for {owner}/{repo}"
    raise RuntimeError(message)


def get_latest_release(api: GitHubAPI, owner: str, repo: str) -> dict | None:
    """Fetch the most recent non-prerelease GitHub release."""
    releases = api.get(f"/repos/{owner}/{repo}/releases", params={"per_page": "100"})
    stable = [
        rel for rel in releases if not rel.get("draft") and not rel.get("prerelease")
    ]
    if not stable:
        return None
    stable.sort(
        key=lambda rel: rel.get("published_at") or rel.get("created_at") or "",
        reverse=True,
    )
    return stable[0]


def get_repo_metadata(api: GitHubAPI, owner: str, repo: str) -> dict:
    """Return repository metadata required for release resolution."""
    return api.get(f"/repos/{owner}/{repo}")


def resolve_action(
    api: GitHubAPI, repo: str, previous_refs: Sequence[str]
) -> ActionResolution:
    """Resolve the newest stable release (or default branch) for an action."""
    owner, name = repo.split("/", 1)
    metadata = get_repo_metadata(api, owner, name)
    if metadata.get("archived"):
        message = f"Repository {repo} is archived; skipping."
        raise RuntimeError(message)
    release = get_latest_release(api, owner, name)
    if release:
        tag = release["tag_name"]
        published = release.get("published_at") or release.get("created_at")
        if not published:
            message = f"Release {repo}@{tag} lacks publication date"
            raise RuntimeError(message)
        commit_sha = resolve_tag_to_commit(api, owner, name, tag)
        comment_label = f"{repo}@{tag}"
        return ActionResolution(
            repo=repo,
            previous_refs=list(previous_refs),
            commit_sha=commit_sha,
            comment_label=comment_label,
            published_date=iso_date(published),
            display_tag=tag,
            release_url=release.get("html_url", metadata.get("html_url", "")),
        )
    default_branch = metadata.get("default_branch", "main")
    commit = api.get(
        f"/repos/{owner}/{name}/commits/{parse.quote(default_branch, safe='')}"
    )
    commit_sha = commit["sha"]
    date_str = commit["commit"]["committer"]["date"]
    comment_label = f"{repo}@default-branch {default_branch}"
    return ActionResolution(
        repo=repo,
        previous_refs=list(previous_refs),
        commit_sha=commit_sha,
        comment_label=comment_label,
        published_date=iso_date(date_str),
        display_tag=comment_label,
        release_url=commit.get("html_url", metadata.get("html_url", "")),
        note="No releases; pinned to default branch commit.",
    )


def build_updates(
    occurrences: dict[str, list[ActionOccurrence]],
    resolutions: dict[str, ActionResolution],
) -> dict[Path, tuple[str, str]]:
    """Return a mapping of files to their original and updated contents.

    Args:
        occurrences: Action references grouped by repository.
        resolutions: Resolved action metadata keyed by repository.

    Returns:
        Mapping of workflow paths to tuples of ``(original_text, updated_text)``.
    """
    updates: dict[Path, tuple[str, str]] = {}
    file_occurrences: dict[Path, list[tuple[ActionOccurrence, ActionResolution]]] = {}
    for repo, occs in occurrences.items():
        resolution = resolutions.get(repo)
        if not resolution:
            continue
        for occ in occs:
            file_occurrences.setdefault(occ.path, []).append((occ, resolution))

    for path, file_occs in file_occurrences.items():
        original_text = path.read_text(encoding="utf-8")
        lines = original_text.splitlines()
        for occ, resolution in file_occs:
            lines[occ.line_index] = normalise_uses_line(
                lines[occ.line_index],
                commit_sha=resolution.commit_sha,
                comment_label=resolution.comment_label,
                published_date=resolution.published_date,
            )
        updated_text = "\n".join(lines) + "\n"
        if updated_text != original_text:
            updates[path] = (original_text, updated_text)
    return updates


def emit_diffs(updates: dict[Path, tuple[str, str]]) -> None:
    """Write unified diffs for pending workflow updates to stdout.

    Args:
        updates: Mapping of workflow paths to their original and updated
            contents.
    """
    for path in sorted(updates):
        original_text, updated_text = updates[path]
        diff = difflib.unified_diff(
            original_text.splitlines(),
            updated_text.splitlines(),
            fromfile=str(path),
            tofile=str(path),
            lineterm="",
        )
        for line in diff:
            sys.stdout.write(f"{line}\n")


def build_summary(resolutions: dict[str, ActionResolution]) -> str:
    """Render a Markdown table summarising pinned actions."""
    headers = [
        "Action",
        "Previous",
        "New tag",
        "SHA (short)",
        "Release link",
        "Published",
    ]
    rows: list[list[str]] = []
    for repo in sorted(resolutions):
        res = resolutions[repo]
        previous = ", ".join(sorted(set(res.previous_refs)))
        rows.append(
            [
                repo,
                previous,
                res.display_tag,
                res.commit_sha[:7],
                res.release_url,
                res.published_date,
            ]
        )
    widths = [
        max(len(str(row[idx])) for row in [headers, *rows])
        for idx in range(len(headers))
    ]
    lines = [
        "| "
        + " | ".join(f"{headers[idx]:<{widths[idx]}}" for idx in range(len(headers)))
        + " |",
        "| " + " | ".join("-" * widths[idx] for idx in range(len(headers))) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(f"{row[idx]!s:<{widths[idx]}}" for idx in range(len(headers)))
            + " |"
        )
    return "\n".join(lines)


def build_summary_lines(resolutions: dict[str, ActionResolution]) -> list[str]:
    """Construct the multi-line summary message for pinned actions.

    Args:
        resolutions: Resolved action metadata keyed by repository.

    Returns:
        Summary text split into individual lines for logging.
    """
    summary = build_summary(resolutions)
    lines = ["Pinned action summary:", "", summary]
    notes = [res.note for res in resolutions.values() if res.note]
    if notes:
        lines.append("")
        lines.append("Notes:")
        lines.extend(f"- {note}" for note in notes)
    return lines


def resolve_all_actions(
    api: GitHubAPI, occurrences: dict[str, list[ActionOccurrence]]
) -> tuple[dict[str, ActionResolution], list[str]]:
    """Resolve all discovered action references via the GitHub API.

    Args:
        api: GitHub API client used to fetch metadata.
        occurrences: Action references grouped by repository.

    Returns:
        Tuple containing resolved metadata and any error messages.
    """
    resolutions: dict[str, ActionResolution] = {}
    errors: list[str] = []
    for repo, occs in occurrences.items():
        previous_refs = [occ.previous_ref for occ in occs]
        try:
            resolutions[repo] = resolve_action(api, repo, previous_refs)
        except RuntimeError as exc:
            errors.append(str(exc))
    return resolutions, errors


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for pinning actions and printing a summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Rewrite workflow files with pinned action SHAs (deprecated; use --write).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite workflow files with pinned action SHAs.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether workflow files would change; prints a unified diff.",
    )
    args = parser.parse_args(argv)

    if (args.apply or args.write) and args.check:
        parser.error("--check cannot be combined with --apply/--write")

    should_write = args.apply or args.write
    check_only = args.check

    files = list(iter_workflow_files())
    if not files:
        logger.info("No workflow files found.")
        return 0

    occurrences = collect_occurrences(files)
    if not occurrences:
        logger.info("No third-party actions found.")
        return 0

    token = os.getenv("GITHUB_TOKEN")
    api = GitHubAPI(token)

    resolutions, errors = resolve_all_actions(api, occurrences)
    if errors:
        error_block = "\n".join(f"- {err}" for err in errors)
        logger.error("Encountered issues while resolving actions:\n%s", error_block)
    if not resolutions:
        return 1

    updates = build_updates(occurrences, resolutions)
    lines = build_summary_lines(resolutions)
    exit_code = 1 if errors else 0
    if check_only:
        if updates:
            emit_diffs(updates)
            exit_code = 1
        logger.info("\n".join(lines))
        return exit_code

    if should_write:
        for path, (_, updated_text) in updates.items():
            path.write_text(updated_text, encoding="utf-8")

    logger.info("\n".join(lines))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
