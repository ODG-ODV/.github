
#!/usr/bin/env python3
"""Audit and synchronize GitHub release labels and configuration."""

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LABELS_FILE = ROOT / "config" / "release-labels.json"
RELEASE_FILE = ROOT / "config" / "release.yml"

ORG = "ODG-ODV"

REPOSITORIES = [
    "scms",
    "appointment-bookings",
    "cfa-app",
    "cfa-scms",
    "kiosk-dashboard",
    "kiosk-mobile-app",
    "bursaryApp",
]


def run_command(command):
    """Execute a command and return stdout, raising on failure."""
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\n"
            f"{result.stderr.strip()}"
        )

    return result.stdout


def github_api(endpoint, paginate=False):
    """Execute a read-only GitHub API request."""
    command = ["gh", "api", "--method", "GET"]

    if paginate:
        command.extend(["--paginate", "--slurp"])

    command.append(endpoint)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        if "HTTP 404" in result.stderr:
            return None

        raise RuntimeError(
            f"GitHub API request failed: {endpoint}\n"
            f"{result.stderr.strip()}"
        )

    data = json.loads(result.stdout)

    if paginate:
        return [
            item
            for page in data
            for item in page
        ]

    return data


def get_repository_labels(repository):
    """Retrieve all repository labels, including paginated results."""
    endpoint = f"repos/{ORG}/{repository}/labels?per_page=100"
    labels = github_api(endpoint, paginate=True)

    if labels is None:
        raise RuntimeError(
            f"Cannot retrieve labels for {ORG}/{repository}"
        )

    return {label["name"]: label for label in labels}


def get_label_changes(existing, expected_labels):
    """Determine which standard labels need creation or updating."""
    changes = []

    for expected in expected_labels:
        name = expected["name"]
        current = existing.get(name)

        if current is None:
            changes.append(("CREATE", expected))
            continue

        current_color = current.get("color", "").lower()
        expected_color = expected["color"].lower()

        current_description = current.get("description") or ""
        expected_description = expected["description"]

        if (
            current_color != expected_color
            or current_description != expected_description
        ):
            changes.append(("UPDATE", expected))

    return changes


def check_labels(repository, expected_labels):
    """Report missing or differing standard labels."""
    existing = get_repository_labels(repository)

    return get_label_changes(existing, expected_labels)


def sync_labels(repository, expected_labels):
    """Create or update standard labels without deleting other labels."""
    changes = check_labels(repository, expected_labels)

    for action, label in changes:
        name = label["name"]

        if action == "CREATE":
            command = [
                "gh", "label", "create", name,
                "--repo", f"{ORG}/{repository}",
                "--color", label["color"],
                "--description", label["description"],
            ]

        elif action == "UPDATE":
            command = [
                "gh", "label", "edit", name,
                "--repo", f"{ORG}/{repository}",
                "--color", label["color"],
                "--description", label["description"],
            ]

        else:
            raise RuntimeError(f"Unsupported action: {action}")

        run_command(command)
        print(f"  {action}D label: {name}")

    return len(changes)


def check_release_config(repository, expected_content):
    """Compare release.yml with the repository's default branch."""
    endpoint = (
        f"repos/{ORG}/{repository}/contents/.github/release.yml"
    )

    result = github_api(endpoint)

    if result is None:
        return "CREATE"

    if result.get("encoding") != "base64":
        raise RuntimeError(
            f"Unexpected content encoding in {ORG}/{repository}"
        )

    current = base64.b64decode(
        result["content"],
        validate=False,
    ).decode("utf-8")

    if current != expected_content:
        return "UPDATE"

    return None


def load_configuration():
    """Load and validate the centralized configuration."""
    labels_data = json.loads(
        LABELS_FILE.read_text(encoding="utf-8")
    )

    expected_labels = labels_data["labels"]

    if not isinstance(expected_labels, list):
        raise ValueError("'labels' must be an array")

    names = set()

    for label in expected_labels:
        if not all(
            key in label for key in ("name", "color", "description")
        ):
            raise ValueError(
                "Each label requires name, color, and description"
            )

        if label["name"] in names:
            raise ValueError(
                f"Duplicate label: {label['name']}"
            )

        names.add(label["name"])

    expected_release = RELEASE_FILE.read_text(
        encoding="utf-8"
    )

    return expected_labels, expected_release


def audit_repository(repository, expected_labels, expected_release):
    """Perform a read-only audit of one repository."""
    print(f"\n=== {ORG}/{repository} ===")

    label_changes = check_labels(repository, expected_labels)

    release_change = check_release_config(
        repository,
        expected_release,
    )

    for action, label in label_changes:
        print(f"  WOULD {action} label: {label['name']}")

    if release_change:
        print(
            f"  WOULD {release_change} .github/release.yml"
        )

    if not label_changes and not release_change:
        print("  Configuration matches")

    return bool(label_changes or release_change)


def apply_repository(repository, expected_labels, expected_release):
    """Synchronize labels only; repository files remain unchanged."""
    print(f"\n=== {ORG}/{repository} ===")

    count = sync_labels(repository, expected_labels)

    if count == 0:
        print("  Labels already match")

    release_change = check_release_config(
        repository,
        expected_release,
    )

    if release_change:
        print(
            f"  WOULD {release_change} .github/release.yml "
            "(PR synchronization pending)"
        )
    else:
        print("  Release configuration matches")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Audit or synchronize GitHub release configuration"
        )
    )

    parser.add_argument(
        "--repo",
        choices=REPOSITORIES,
        help="Target one repository (default: all participating repos)",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Create/update standard labels. "
            "Does not modify release.yml files."
        ),
    )

    args = parser.parse_args()

    try:
        expected_labels, expected_release = load_configuration()

        repositories = (
            [args.repo] if args.repo else REPOSITORIES
        )

        changes_found = False

        for repository in repositories:
            if args.apply:
                apply_repository(
                    repository,
                    expected_labels,
                    expected_release,
                )
            else:
                changed = audit_repository(
                    repository,
                    expected_labels,
                    expected_release,
                )
                changes_found |= changed

        if args.apply:
            print("\nLabel synchronization complete.")
            print(
                "Release configuration files were not modified."
            )
        else:
            print(
                "\nDry run complete. No repositories were modified."
            )

            if changes_found:
                print("Configuration differences detected.")
            else:
                print("All audited repositories match.")

        return 0

    except (
        RuntimeError,
        ValueError,
        KeyError,
        OSError,
        UnicodeError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
