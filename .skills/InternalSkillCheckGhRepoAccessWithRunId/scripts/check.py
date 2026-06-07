#!/usr/bin/env python3
"""Check gh CLI availability and repository access per .theloop/repo.txt.

Usage: .skills/InternalSkillCheckGhRepoAccessWithRunId/scripts/check.py   (from the repository root)
Output: JSON object with repo_url, a checks array, and an actions array. Each check
has check, status, detail, and suggestion (both null unless the check fails or is
skipped with context). actions lists human-readable side effects (for example, a
label that was created); it is [] when nothing was changed.
Exit code: 0 when all non-skipped checks pass, 1 otherwise.
"""
import json
import os
import re
import shutil
import subprocess
import sys

REPO_FILE = os.path.join(".theloop", "repo.txt")
INSTALL_SUGGESTION = (
    "Install the GitHub CLI from https://cli.github.com/ "
    "(for example, `brew install gh` on macOS)."
)
AUTH_SUGGESTION = "Authenticate with `gh auth login`."
REPO_CONFIG_SUGGESTION = (
    "Create `.theloop/repo.txt` containing a single line with the GitHub repository URL "
    "this project needs to access (for example, `https://github.com/owner/repo`)."
)
THELOOP_LABEL = "theloop"
THELOOP_LABEL_DESCRIPTION = "Issues and pull requests tracked by theloop"


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def add(checks, name, status, detail=None, suggestion=None):
    checks.append({
        "check": name,
        "status": status,
        "detail": detail,
        "suggestion": suggestion,
    })


def parse_repo_slug(url):
    url = url.strip()
    if not url:
        return None
    if re.fullmatch(r"[^/\s]+/[^/\s]+", url):
        return url.rstrip("/").removesuffix(".git")
    match = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None


def clone_url(slug):
    return f"https://github.com/{slug}.git"


def gh_repo_view(slug):
    proc = run(["gh", "repo", "view", slug, "--json", "name", "-q", ".name"])
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "gh repo view failed").strip()
        return False, detail
    return True, None


def git_ls_remote(url):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    proc = run(["git", "ls-remote", url, "HEAD"], env=env)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "git ls-remote failed").strip()
        return False, detail
    if not proc.stdout.strip():
        return False, "git ls-remote returned no refs"
    return True, None


def gh_label_exists(slug, name):
    proc = run(["gh", "api", f"repos/{slug}/labels/{name}"])
    return proc.returncode == 0


def ensure_theloop_label(slug):
    if gh_label_exists(slug, THELOOP_LABEL):
        return True, None, False
    proc = run([
        "gh", "label", "create", THELOOP_LABEL,
        "-R", slug,
        "-d", THELOOP_LABEL_DESCRIPTION,
    ])
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "gh label create failed").strip()
        return False, detail, False
    return True, None, True


def skip_label_checks(checks, reason):
    add(checks, "gh-label-theloop", "skipped", reason, None)


def main():
    checks = []
    actions = []
    repo_url = None
    slug = None
    can_use_gh = False
    can_use_repo = False

    if not os.path.isfile(REPO_FILE):
        add(
            checks,
            "repo-config",
            "fail",
            f"{REPO_FILE} is missing; the target repository is not configured for this project.",
            REPO_CONFIG_SUGGESTION,
        )
    else:
        with open(REPO_FILE) as f:
            repo_url = f.read().strip()
        if not repo_url:
            add(
                checks,
                "repo-config",
                "fail",
                f"{REPO_FILE} is empty; the target repository is not configured for this project.",
                REPO_CONFIG_SUGGESTION,
            )
        else:
            slug = parse_repo_slug(repo_url)
            if not slug:
                add(
                    checks,
                    "repo-config",
                    "fail",
                    f"{REPO_FILE} does not contain a recognizable GitHub repository URL: {repo_url!r}",
                    REPO_CONFIG_SUGGESTION,
                )
            else:
                add(checks, "repo-config", "pass")
                can_use_repo = True

    if shutil.which("gh") is None:
        add(
            checks,
            "gh-installed",
            "fail",
            "The `gh` command is not available on PATH.",
            INSTALL_SUGGESTION,
        )
        add(checks, "gh-authenticated", "skipped", "Skipped because `gh` is not installed.", None)
        add(checks, "gh-repo-access", "skipped", "Skipped because `gh` is not installed.", None)
        add(checks, "gh-repo-pull", "skipped", "Skipped because `gh` is not installed.", None)
        skip_label_checks(checks, "Skipped because `gh` is not installed.")
    else:
        add(checks, "gh-installed", "pass")
        can_use_gh = True

        auth = run(["gh", "auth", "status"])
        if auth.returncode != 0:
            detail = (auth.stderr or auth.stdout or "gh auth status failed").strip()
            add(checks, "gh-authenticated", "fail", detail, AUTH_SUGGESTION)
            add(
                checks,
                "gh-repo-access",
                "skipped",
                "Skipped because `gh` is not authenticated.",
                None,
            )
            add(
                checks,
                "gh-repo-pull",
                "skipped",
                "Skipped because `gh` is not authenticated.",
                None,
            )
            skip_label_checks(checks, "Skipped because `gh` is not authenticated.")
        else:
            add(checks, "gh-authenticated", "pass")

            if not can_use_repo:
                add(
                    checks,
                    "gh-repo-access",
                    "skipped",
                    "Skipped because the repository URL is not configured.",
                    None,
                )
                add(
                    checks,
                    "gh-repo-pull",
                    "skipped",
                    "Skipped because the repository URL is not configured.",
                    None,
                )
                skip_label_checks(checks, "Skipped because the repository URL is not configured.")
            else:
                ok, detail = gh_repo_view(slug)
                if ok:
                    add(checks, "gh-repo-access", "pass")
                    label_ok, label_detail, created = ensure_theloop_label(slug)
                    if label_ok:
                        add(checks, "gh-label-theloop", "pass")
                        if created:
                            actions.append(
                                f"Created label `{THELOOP_LABEL}` on {slug} for bugs and pull requests."
                            )
                    else:
                        add(
                            checks,
                            "gh-label-theloop",
                            "fail",
                            f"Cannot ensure label `{THELOOP_LABEL}` on {slug}: {label_detail}",
                            (
                                f"Verify that your GitHub account can manage labels on {repo_url} "
                                f"(for example, run `gh label create {THELOOP_LABEL} -R {slug}`)."
                            ),
                        )
                    pull_ok, pull_detail = git_ls_remote(clone_url(slug))
                    if pull_ok:
                        add(checks, "gh-repo-pull", "pass")
                    else:
                        add(
                            checks,
                            "gh-repo-pull",
                            "fail",
                            f"Cannot read from {slug}: {pull_detail}",
                            (
                                "Verify that `gh auth setup-git` has been run and that your account "
                                f"can clone or pull from {repo_url}."
                            ),
                        )
                else:
                    add(
                        checks,
                        "gh-repo-access",
                        "fail",
                        f"Cannot access {slug}: {detail}",
                        (
                            f"Verify that the URL in {REPO_FILE} is correct and that your GitHub "
                            "account has access to this repository."
                        ),
                    )
                    add(
                        checks,
                        "gh-repo-pull",
                        "skipped",
                        "Skipped because repository access via `gh` failed.",
                        None,
                    )
                    skip_label_checks(checks, "Skipped because repository access via `gh` failed.")

    result = {"repo_url": repo_url, "checks": checks, "actions": actions}
    print(json.dumps(result, indent=2))
    passed = all(c["status"] in {"pass", "skipped"} for c in checks)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
