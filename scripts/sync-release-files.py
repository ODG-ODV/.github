
#!/usr/bin/env python3
"""Synchronize GitHub release-note configuration via pull requests."""

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

ORG = "ODG-ODV"
BASE_BRANCH = "develop"
SYNC_BRANCH = "chore/sync-release-config"
TARGET_FILE = ".github/release.yml"

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "config" / "release.yml"

REPOSITORIES = [
    "scms",
    "appointment-bookings",
    "cfa-app",
    "cfa-scms",
    "kiosk-dashboard",
    "kiosk-mobile-app",
    "bursaryApp",
]


def run(command, input_text=None):
    result = subprocess.run(
        command,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\n"
            f"{result.stderr.strip()}"
        )

    return result.stdout.strip()


def gh_api(endpoint, method="GET", data=None):
    command = [
        "gh", "api", "--method", method, endpoint
    ]

    if data is not None:
        command.extend(["--input", "-"])
        output = run(command, json.dumps(data))
    else:
        output = run(command)

    return json.loads(output) if output else None


def get_optional(endpoint):
    """Return None for 404; raise for all other API errors."""
    result = subprocess.run(
        ["gh", "api", "--method", "GET", endpoint],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        return json.loads(result.stdout)

    if "HTTP 404" in result.stderr:
        return None

    raise RuntimeError(result.stderr.strip())


def get_branch(repo, branch):
    return get_optional(
        f"repos/{ORG}/{repo}/branches/{branch}"
    )


def get_file(repo, branch):
    result = get_optional(
        f"repos/{ORG}/{repo}/contents/{TARGET_FILE}?ref={branch}"
    )

    if result is None:
        return None

    if result.get("encoding") != "base64":
        raise RuntimeError("Unexpected content encoding")

    return base64.b64decode(
        result["content"]
    ).decode("utf-8")


def get_pr(repo):
    """Find an existing open synchronization PR."""
    result = gh_api(
        f"repos/{ORG}/{repo}/pulls"
        f"?state=open&head={ORG}:{SYNC_BRANCH}"
        f"&base={BASE_BRANCH}"
    )

    return result[0] if result else None


def branch_commit(repo, branch):
    data = get_branch(repo, branch)
    return data["commit"]["sha"] if data else None


def create_branch(repo, sha):
    gh_api(
        f"repos/{ORG}/{repo}/git/refs",
        method="POST",
        data={
            "ref": f"refs/heads/{SYNC_BRANCH}",
            "sha": sha,
        },
    )


def update_file(repo, content, existing_sha):
    endpoint = (
        f"repos/{ORG}/{repo}/contents/{TARGET_FILE}"
    )

    payload = {
        "message": "ci: synchronize release notes configuration",
        "content": base64.b64encode(
            content.encode("utf-8")
        ).decode("ascii"),
        "branch": SYNC_BRANCH,
    }

    if existing_sha:
        payload["sha"] = existing_sha

    gh_api(endpoint, method="PUT", data=payload)


def sync_repository(repo, desired, apply):
    print(f"\n=== {ORG}/{repo} ===")

    base = get_branch(repo, BASE_BRANCH)

    if base is None:
        raise RuntimeError(f"{repo}: develop branch not found")

    base_sha = base["commit"]["sha"]
    current = get_file(repo, BASE_BRANCH)

    if current == desired:
        print("  Configuration matches develop")
        return

    pr = get_pr(repo)
    sync_sha = branch_commit(repo, SYNC_BRANCH)

    if sync_sha and not pr:
        raise RuntimeError(
            f"{repo}: synchronization branch exists "
            "without an open PR; refusing to overwrite it"
        )

    if not apply:
        print(
            "  WOULD CREATE/UPDATE pull request "
            f"against {BASE_BRANCH}"
        )
        return

    if not sync_sha:
        create_branch(repo, base_sha)
        print(f"  Created branch: {SYNC_BRANCH}")

    existing = get_optional(
        f"repos/{ORG}/{repo}/contents/{TARGET_FILE}"
        f"?ref={SYNC_BRANCH}"
    )

    existing_sha = existing["sha"] if existing else None

    update_file(repo, desired, existing_sha)
    print(f"  Updated {TARGET_FILE}")

    if pr:
        print(f"  Updated existing PR: {pr['html_url']}")
        return

    result = gh_api(
        f"repos/{ORG}/{repo}/pulls",
        method="POST",
        data={
            "title": "ci: synchronize release notes configuration",
            "head": SYNC_BRANCH,
            "base": BASE_BRANCH,
            "body": (
                "Synchronizes `.github/release.yml` "
                "with the organization's centralized "
                "release-note configuration.\n\n"
                "No application or deployment changes."
            ),
        },
    )

    print(f"  Created PR: {result['html_url']}")


def main():
    parser = argparse.ArgumentParser(
        description="Synchronize release.yml through PRs"
    )

    parser.add_argument(
        "--repo",
        choices=REPOSITORIES,
        help="Target one repository (default: all)",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create or update synchronization PRs",
    )

    args = parser.parse_args()

    try:
        desired = SOURCE_FILE.read_text(encoding="utf-8")

        repos = [args.repo] if args.repo else REPOSITORIES

        failures = 0

        for repo in repos:
            try:
                sync_repository(repo, desired, args.apply)
            except (RuntimeError, ValueError, KeyError) as exc:
                failures += 1
                print(f"  ERROR: {exc}", file=sys.stderr)

        if failures:
            print(f"\nCompleted with {failures} error(s).")
            return 1

        if args.apply:
            print("\nSynchronization completed.")
        else:
            print("\nDry run completed. No changes made.")

        return 0

    except (OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
