#!/usr/bin/env python3
"""Pin GitHub Actions in workflow files to the latest stable release SHAs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence
from urllib import error, parse, request

WORKFLOW_DIR = Path(".github/workflows")
USES_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?P<dash>-\s+)?uses:\s*(?P<quote>['\"]?)(?P<value>[^'\"#]+?)(?P=quote)\s*(#.*)?$"
)
PIN_COMMENT_PREFIX = "# pinned:"


class GitHubAPI:
    """Minimal helper for GitHub REST API requests."""

    def __init__(self, token: Optional[str]) -> None:
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

    def get(self, path: str, *, params: Optional[Dict[str, str]] = None) -> dict:
        url = f"{self._base_url}{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"
        req = request.Request(url, headers=self._headers)
        try:
            with request.urlopen(  # noqa: S310 - GitHub API client  # nosec B310  # pdf-toolbox: GitHub API requests rely on urllib with pinned CA bundle | issue:-
                req, context=self._context
            ) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload)
        except error.HTTPError as exc:  # pragma: no cover - network failures are rare  # pdf-toolbox: log and rethrow network errors for diagnostics | issue:-
            message = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"GitHub API request failed for {url}: {exc}\n{message}") from exc


@dataclass
class ActionOccurrence:
    path: Path
    line_index: int
    leading: str
    quote: str
    repo: str
    subpath: str
    previous_ref: str


@dataclass
class ActionResolution:
    repo: str
    previous_refs: List[str]
    commit_sha: str
    comment_label: str
    published_date: str
    display_tag: str
    release_url: str
    note: Optional[str] = None


def iter_workflow_files() -> Iterable[Path]:
    if not WORKFLOW_DIR.exists():
        return []
    return sorted(path for path in WORKFLOW_DIR.glob("**/*.yml") if path.is_file())


def parse_uses_lines(path: Path) -> List[ActionOccurrence]:
    occurrences: List[ActionOccurrence] = []
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
        if len(segments) < 2:
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


def collect_occurrences(files: Iterable[Path]) -> Dict[str, List[ActionOccurrence]]:
    action_map: Dict[str, List[ActionOccurrence]] = {}
    for path in files:
        for occurrence in parse_uses_lines(path):
            action_map.setdefault(occurrence.repo, []).append(occurrence)
    return action_map


def iso_date(date_str: str) -> str:
    parsed = dt.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return parsed.date().isoformat()


def resolve_tag_to_commit(api: GitHubAPI, owner: str, repo: str, tag: str) -> str:
    encoded_tag = parse.quote(tag, safe="")
    data = api.get(f"/repos/{owner}/{repo}/git/refs/tags/{encoded_tag}")
    ref_obj: Optional[dict]
    if isinstance(data, list):
        ref_obj = next((item for item in data if item.get("ref") == f"refs/tags/{tag}"), None)
        if ref_obj is None:
            raise RuntimeError(f"Unable to resolve tag {tag} for {owner}/{repo}")
    else:
        ref_obj = data
    obj = ref_obj["object"]
    if obj["type"] == "tag":
        tag_data = api.get(f"/repos/{owner}/{repo}/git/tags/{obj['sha']}")
        return tag_data["object"]["sha"]
    if obj["type"] == "commit":
        return obj["sha"]
    raise RuntimeError(f"Unsupported tag object type {obj['type']} for {owner}/{repo}")


def get_latest_release(api: GitHubAPI, owner: str, repo: str) -> Optional[dict]:
    releases = api.get(f"/repos/{owner}/{repo}/releases", params={"per_page": "100"})
    stable = [rel for rel in releases if not rel.get("draft") and not rel.get("prerelease")]
    if not stable:
        return None
    stable.sort(key=lambda rel: rel.get("published_at") or rel.get("created_at") or "", reverse=True)
    return stable[0]


def get_repo_metadata(api: GitHubAPI, owner: str, repo: str) -> dict:
    return api.get(f"/repos/{owner}/{repo}")


def resolve_action(api: GitHubAPI, repo: str, previous_refs: Sequence[str]) -> ActionResolution:
    owner, name = repo.split("/", 1)
    metadata = get_repo_metadata(api, owner, name)
    if metadata.get("archived"):
        raise RuntimeError(f"Repository {repo} is archived; skipping.")
    release = get_latest_release(api, owner, name)
    if release:
        tag = release["tag_name"]
        published = release.get("published_at") or release.get("created_at")
        if not published:
            raise RuntimeError(f"Release {repo}@{tag} lacks publication date")
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
    occurrences: Dict[str, List[ActionOccurrence]], resolutions: Dict[str, ActionResolution]
) -> None:
    for repo, occs in occurrences.items():
        if repo not in resolutions:
            continue
        resolution = resolutions[repo]
        by_file: Dict[Path, List[ActionOccurrence]] = {}
        for occ in occs:
            by_file.setdefault(occ.path, []).append(occ)
        for path, file_occs in by_file.items():
            lines = path.read_text(encoding="utf-8").splitlines()
            for occ in file_occs:
                base_value = occ.repo
                if occ.subpath:
                    base_value = f"{base_value}/{occ.subpath}"
                quoted = f"{occ.quote}{base_value}@{resolution.commit_sha}{occ.quote}"
                comment = (
                    f" {PIN_COMMENT_PREFIX} {resolution.comment_label} ({resolution.published_date})"
                )
                lines[occ.line_index] = f"{occ.leading}uses: {quoted}{comment}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_summary(resolutions: Dict[str, ActionResolution]) -> str:
    headers = [
        "Action",
        "Previous",
        "New tag",
        "SHA (short)",
        "Release link",
        "Published",
    ]
    rows: List[List[str]] = []
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
    widths = [max(len(str(row[idx])) for row in [headers] + rows) for idx in range(len(headers))]
    lines = [
        "| "
        + " | ".join(f"{headers[idx]:<{widths[idx]}}" for idx in range(len(headers)))
        + " |",
        "| " + " | ".join("-" * widths[idx] for idx in range(len(headers))) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(f"{str(row[idx]):<{widths[idx]}}" for idx in range(len(headers)))
            + " |"
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Rewrite workflow files with pinned action SHAs.",
    )
    args = parser.parse_args(argv)

    files = list(iter_workflow_files())
    if not files:
        print("No workflow files found.")
        return 0

    occurrences = collect_occurrences(files)
    if not occurrences:
        print("No third-party actions found.")
        return 0

    token = os.getenv("GITHUB_TOKEN")
    api = GitHubAPI(token)

    resolutions: Dict[str, ActionResolution] = {}
    errors: List[str] = []
    for repo, occs in occurrences.items():
        previous_refs = [occ.previous_ref for occ in occs]
        try:
            resolutions[repo] = resolve_action(api, repo, previous_refs)
        except RuntimeError as exc:
            errors.append(str(exc))

    if errors:
        error_block = "\n".join(f"- {err}" for err in errors)
        print("Encountered issues while resolving actions:\n" + error_block, file=sys.stderr)
    if not resolutions:
        return 1

    if args.apply:
        apply_updates(occurrences, resolutions)

    print("Pinned action summary:\n")
    print(build_summary(resolutions))
    notes = [res.note for res in resolutions.values() if res.note]
    if notes:
        print("\nNotes:")
        for note in notes:
            print(f"- {note}")

    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
