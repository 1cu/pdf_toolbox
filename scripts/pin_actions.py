#!/usr/bin/env python3
"""Pin GitHub Actions in workflow files to the latest stable release SHAs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import re
import ssl
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib import error, parse, request

try:
    from pdf_toolbox.utils import logger as _project_logger
except ImportError:  # pragma: no cover - fallback for isolated script runs  # pdf-toolbox: allow standalone use when package logging unavailable | issue:-
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger("pdf_toolbox.scripts.pin_actions")
else:
    logger = _project_logger.getChild("scripts.pin_actions")

WORKFLOW_DIR = Path(".github/workflows")
USES_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?P<dash>-\s+)?uses:\s*(?P<quote>['\"]?)(?P<value>[^'\"#]+?)(?P=quote)\s*(#.*)?$"
)
PIN_COMMENT_PREFIX = "# pinned:"
MIN_REPO_SEGMENTS = 2


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
        if scheme not in {"https", "http"}:
            message = f"Unsupported URL scheme for GitHub API: {scheme}"
            raise ValueError(message)
        req = request.Request(  # noqa: S310  # pdf-toolbox: validated HTTPS request to GitHub API | issue:-
            url, headers=self._headers
        )
        try:
            with request.urlopen(  # noqa: S310 - GitHub API client  # nosec B310  # pdf-toolbox: GitHub API requests rely on urllib with pinned CA bundle | issue:-
                req, context=self._context
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
    return sorted(path for path in WORKFLOW_DIR.glob("**/*.yml") if path.is_file())


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
    comment_label = f"default-branch {default_branch}"
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


def apply_updates(
    occurrences: dict[str, list[ActionOccurrence]],
    resolutions: dict[str, ActionResolution],
) -> None:
    """Rewrite workflow files with the resolved SHAs and annotations."""
    for repo, occs in occurrences.items():
        if repo not in resolutions:
            continue
        resolution = resolutions[repo]
        by_file: dict[Path, list[ActionOccurrence]] = {}
        for occ in occs:
            by_file.setdefault(occ.path, []).append(occ)
        for path, file_occs in by_file.items():
            lines = path.read_text(encoding="utf-8").splitlines()
            for occ in file_occs:
                base_value = occ.repo
                if occ.subpath:
                    base_value = f"{base_value}/{occ.subpath}"
                quoted = f"{occ.quote}{base_value}@{resolution.commit_sha}{occ.quote}"
                comment = f" {PIN_COMMENT_PREFIX} {resolution.comment_label} ({resolution.published_date})"
                lines[occ.line_index] = f"{occ.leading}uses: {quoted}{comment}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for pinning actions and printing a summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Rewrite workflow files with pinned action SHAs.",
    )
    args = parser.parse_args(argv)

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

    resolutions: dict[str, ActionResolution] = {}
    errors: list[str] = []
    for repo, occs in occurrences.items():
        previous_refs = [occ.previous_ref for occ in occs]
        try:
            resolutions[repo] = resolve_action(api, repo, previous_refs)
        except RuntimeError as exc:
            errors.append(str(exc))

    if errors:
        error_block = "\n".join(f"- {err}" for err in errors)
        logger.error("Encountered issues while resolving actions:\n%s", error_block)
    if not resolutions:
        return 1

    if args.apply:
        apply_updates(occurrences, resolutions)

    summary = build_summary(resolutions)
    lines = ["Pinned action summary:", "", summary]
    notes = [res.note for res in resolutions.values() if res.note]
    if notes:
        lines.append("")
        lines.append("Notes:")
        lines.extend(f"- {note}" for note in notes)
    logger.info("\n".join(lines))

    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
