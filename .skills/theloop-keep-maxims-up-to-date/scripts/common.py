"""Shared helpers for the theloop-keep-maxims-up-to-date skill.

This is a non-entry-point library module: the skill's entry-point scripts import
it; the runner never invokes it directly. It owns the paths, the metadata I/O, the
atomic compare-and-swap that keeps `maxims/metadata.json` consistent under
concurrent and interrupted runs, and the thin GitHub adapter built on `gh`.

All paths are relative to the current working directory, which is the repository
root. Standard library only, plus `gh` and `git` on PATH.
"""
import json
import os
import random
import re
import subprocess
import sys
import time
from typing import NoReturn

try:
    import yaml
except ImportError:
    yaml = None

# --- paths the skill owns ----------------------------------------------------

MAXIMS_DIR = "maxims"
METADATA_PATH = os.path.join(MAXIMS_DIR, "metadata.json")
CACHE_DIR = os.path.join(MAXIMS_DIR, "cache")
GITIGNORE_PATH = os.path.join(MAXIMS_DIR, ".gitignore")
GITIGNORE_BODY = ("# transient and cached files under maxims/ — never committed\n"
                  "cache/\n*.tmp\n*.lock\n")
REPO_FILE = os.path.join(".theloop", "repo.txt")
# Version of this generator, stamped into every metadata.json (YYYYMMDD).
GENERATOR_VERSION = "20260608"

# Suggested default categories — the taxonomy is open, new ones are created on
# demand. Used only to give a new category file a tidy title; never seeded into
# metadata, which lists only the category files that actually exist.
DEFAULT_TITLES = {
    "frontend": "Frontend",
    "backend": "Backend",
    "javascript": "JavaScript",
    "html": "HTML",
    "css": "CSS",
    "data-flow": "Data flow",
    "database": "Database",
    "sql-patterns": "SQL patterns",
    "naming": "Naming",
}


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


# --- identity & naming -------------------------------------------------------

def slug(text):
    """Lowercase kebab slug: the stable, category-independent identity basis."""
    s = re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower()).strip("-")
    return s or "untitled"


def category_basename(category_id):
    """UPPERCASE, hyphens kept: data-flow -> DATA-FLOW, sql-patterns -> SQL-PATTERNS."""
    return slug(category_id).upper()


def category_yml(category_id):
    return category_basename(category_id) + ".yml"


def category_md(category_id):
    return category_basename(category_id) + ".md"


def category_title(category_id):
    cid = slug(category_id)
    return DEFAULT_TITLES.get(cid, cid.replace("-", " ").capitalize())


def maxim_id(title):
    """A maxim's stable id is derived from its title alone, never its category, so
    moving a maxim between categories does not change its id."""
    return slug(title)


# --- the .yml source of truth and the .md generated from it ------------------

def require_yaml():
    if yaml is None:
        die("PyYAML is required by the maxims skill but is not installed; "
            "install it (for example, pip install pyyaml) and retry")


def load_category_text(text):
    require_yaml()
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        die(f"invalid YAML: {exc}")
    if data is None:
        return {}
    if not isinstance(data, dict):
        die("a category .yml must be a YAML mapping with category, title, and maxims")
    return data


def load_category(path):
    """Parse a category's .yml source-of-truth file into a dict."""
    with open(path, encoding="utf-8") as f:
        return load_category_text(f.read())


def dump_category(cat):
    """Serialize a category dict back to .yml text, deterministically."""
    require_yaml()
    return yaml.safe_dump(cat, sort_keys=False, allow_unicode=True, default_flow_style=False)


def evidence_line(ev):
    parts = [f"PR #{ev['pr']}"]
    pair = ev.get("commit_pair")
    if pair and len(pair) == 2 and all(pair):
        parts.append(f"({pair[0]} → {pair[1]})")
    if ev.get("comment_by"):
        parts.append(f"via @{ev['comment_by']}")
    head = " ".join(parts)
    if ev.get("note"):
        head += f" — {ev['note']}"
    return head


def render_md(cat):
    """Render a category's .md from its parsed .yml. The .yml is the single source of
    truth; this output is regenerated and must never be hand-edited."""
    title = cat.get("title") or cat.get("category", "Maxims")
    out = [f"# {title}", "",
           "<!-- generated from this category's .yml file; edit the .yml and regenerate, never edit this .md -->"]
    for m in cat.get("maxims", []):
        out += ["", f"## {m['title']}", "", str(m.get('statement', '')).strip(), "",
                f"- **Status:** {m.get('status', 'proposed')}"]
        if m.get("applies_to"):
            out.append("- **Applies to:** " + ", ".join(f"`{g}`" for g in m["applies_to"]))
        if m.get("rationale"):
            out.append(f"- **Rationale:** {str(m['rationale']).strip()}")
        if m.get("evidence"):
            out.append("- **Evidence:**")
            out += [f"  - {evidence_line(ev)}" for ev in m["evidence"]]
    return "\n".join(out).rstrip("\n") + "\n"


# --- repository identity -----------------------------------------------------

def parse_repo_slug(url):
    url = (url or "").strip()
    if not url:
        return None
    if re.fullmatch(r"[^/\s]+/[^/\s]+", url):
        return url.rstrip("/").removesuffix(".git")
    match = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None


def repo_slug(required=False):
    """owner/name from .theloop/repo.txt, or None. Required only for gh steps."""
    if not os.path.isfile(REPO_FILE):
        if required:
            die(f"{REPO_FILE} is missing; the target repository is not configured")
        return None
    with open(REPO_FILE, encoding="utf-8") as f:
        slug_value = parse_repo_slug(f.read())
    if required and not slug_value:
        die(f"{REPO_FILE} does not contain a recognizable GitHub repository")
    return slug_value


# --- maxims/ state -----------------------------------------------------------

def maxims_state():
    """'absent' (no maxims/), 'foreign' (a maxims/ we did not create), or 'ready'."""
    if not os.path.isdir(MAXIMS_DIR):
        return "absent"
    if not os.path.isfile(METADATA_PATH):
        return "foreign"
    return "ready"


def require_ready():
    """Every script except init refuses to run until maxims/ is initialized, and
    refuses to adopt a maxims/ it did not create (the persistent-artifact guard)."""
    state = maxims_state()
    if state == "absent":
        die("maxims/ is not initialized; run init-maxims.py first")
    if state == "foreign":
        die(f"{MAXIMS_DIR}/ exists but has no metadata.json; it belongs to something "
            f"else — refusing to write into it")


def new_metadata():
    return {
        "generator_version": GENERATOR_VERSION,
        "existing_conventions": [],
        "categories": [],
        "analyzed_prs": [],
    }


def read_metadata():
    require_ready()
    with open(METADATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def dumps(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


# --- atomic, idempotent, lost-update-safe writes -----------------------------

def create_new(path, text):
    """Create a file that must not already exist (O_EXCL), durably. Used for the
    one-time creation of metadata.json and of a brand-new category file."""
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())


def write_text_atomic(path, text, run_id):
    """Durably (over)write a file via a RunId-nonced temp + atomic rename, so a
    reader or a crash never sees a partial file. Used for the .gitignore and the
    per-PR collection cache, where overwriting with identical content is harmless."""
    tmp = f"{path}.{run_id}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def cas_update(path, transform, run_id, *, base=0.020, coeff=1.4, max_attempts=12):
    """Optimistic compare-and-swap on a text file, lock-free.

    Read the file and capture its version token (mtime + size); compute the new
    text via transform(old); write it to a RunId-nonced temp; then, only if the
    file is unchanged since it was read, atomically rename the temp over it. If it
    changed underneath us, delete the temp and retry after a randomized
    exponential backoff (~20 ms base, ~1.4x growth). A transform that returns the
    input unchanged is a no-op — nothing is written. Returns True if it wrote.
    """
    tmp = f"{path}.{run_id}.tmp"
    try:
        for attempt in range(max_attempts):
            st0 = os.stat(path)
            token = (st0.st_mtime_ns, st0.st_size)
            with open(path, encoding="utf-8") as f:
                old = f.read()
            new = transform(old)
            if new == old:
                return False
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(new)
                f.flush()
                os.fsync(f.fileno())
            st1 = os.stat(path)
            if (st1.st_mtime_ns, st1.st_size) == token:
                os.replace(tmp, path)
                return True
            os.remove(tmp)
            time.sleep(random.uniform(0, base * (coeff ** attempt)))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    die(f"{path}: too much write contention; gave up after {max_attempts} attempts")


def update_metadata(mutate, run_id):
    """cas_update specialized to metadata.json: parse, mutate in place, re-dump."""
    def transform(old):
        data = json.loads(old)
        mutate(data)
        return dumps(data)
    return cas_update(METADATA_PATH, transform, run_id)


# --- per-PR collection cache (gitignored; the slow-fetch memo) ----------------

def pr_cache_path(pr):
    return os.path.join(CACHE_DIR, f"{pr}.json")


def read_pr_cache(pr):
    """Return a PR's already-collected digest, or None if it was never fetched. The
    file's existence is the proof that the PR was fully collected and may be reused."""
    path = pr_cache_path(pr)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_pr_cache(pr, digest, run_id):
    """Cache a fully-collected PR digest under the gitignored cache/ dir, atomically,
    so a later run reuses it instead of re-fetching — the slow collect step runs once."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    write_text_atomic(pr_cache_path(pr), dumps(digest), run_id)


# --- GitHub adapter (the only platform-specific surface) ---------------------

class GhError(Exception):
    pass


class GhClient:
    """Thin wrapper over `gh`. Serial by design: concurrent gh processes trip
    GitHub's secondary rate limits, so calls are made one at a time and retried
    with backoff when a rate limit is hit. Every call is time-bounded (per the rule
    on time-bounded operations): a call that exceeds `timeout` seconds raises a
    timeout error rather than hanging. Reimplementing these few methods is all that
    a GitLab/Bitbucket port would require."""

    RATE_HINTS = ("rate limit", "secondary rate", "abuse detection", "was submitted too quickly")

    def __init__(self, slug, *, base=1.0, coeff=2.0, max_attempts=6, timeout=120):
        self.slug = slug
        self.base = base
        self.coeff = coeff
        self.max_attempts = max_attempts
        self.timeout = timeout

    def _run(self, args):
        last = ""
        for attempt in range(self.max_attempts):
            try:
                proc = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=self.timeout)
            except FileNotFoundError:
                raise GhError("the GitHub CLI `gh` is not installed or not on PATH")
            except subprocess.TimeoutExpired:
                raise GhError(f"timeout: `gh {' '.join(args[:2])} …` exceeded {self.timeout}s")
            if proc.returncode == 0:
                return proc.stdout
            last = (proc.stderr or proc.stdout).strip()
            if any(h in last.lower() for h in self.RATE_HINTS) and attempt + 1 < self.max_attempts:
                time.sleep(self.base * (self.coeff ** attempt) + random.uniform(0, 1))
                continue
            break
        raise GhError(last or "gh command failed")

    def _json(self, args):
        try:
            return json.loads(self._run(args))
        except json.JSONDecodeError as exc:
            raise GhError(f"gh returned non-JSON output: {exc}")

    def _probe(self, args, what):
        try:
            return subprocess.run(["gh", *args], capture_output=True, timeout=self.timeout)
        except FileNotFoundError:
            die("the GitHub CLI `gh` is not installed or not on PATH")
        except subprocess.TimeoutExpired:
            die(f"timeout: `gh {what}` did not respond within {self.timeout}s")

    def ensure_access(self):
        """Verify gh is installed, authenticated, and the repo is readable, each
        check time-bounded. The skill only reads pull requests, so it asks for
        nothing more."""
        if self._probe(["--version"], "--version").returncode != 0:
            die("the GitHub CLI `gh` is not installed or not on PATH")
        if self._probe(["auth", "status"], "auth status").returncode != 0:
            die("`gh` is not authenticated; run `gh auth login`")
        try:
            self._run(["repo", "view", self.slug, "--json", "name"])
        except GhError as exc:
            die(f"cannot access repository {self.slug} via gh: {exc}")

    def list_merged_prs(self, limit):
        """Merged PRs only — most recent first. Closed-unmerged and open are
        deliberately excluded: a maxim reflects what was actually adopted."""
        return self._json([
            "pr", "list", "--repo", self.slug, "--state", "merged",
            "--limit", str(limit),
            "--json", "number,title,url,mergedAt,author",
        ])

    def pr_view(self, number):
        return self._json([
            "pr", "view", str(number), "--repo", self.slug,
            "--json", "number,title,url,mergedAt,author,commits,reviews,comments,files",
        ])

    def inline_review_comments(self, number):
        """Inline (path/line) review comments live only in the REST API, not in
        `gh pr view`. These carry the richest reviewer-steering signal."""
        raw = self._json([
            "api", "--paginate",
            f"repos/{self.slug}/pulls/{number}/comments",
        ])
        return [{
            "author": (c.get("user") or {}).get("login"),
            "path": c.get("path"),
            "line": c.get("line") or c.get("original_line"),
            "commit_id": (c.get("commit_id") or "")[:7],
            "body": c.get("body"),
        } for c in raw]

    def commit_files(self, sha):
        """Filenames touched by a single commit, for the reworked-files signal."""
        data = self._json(["api", f"repos/{self.slug}/commits/{sha}"])
        return sorted(f.get("filename") for f in data.get("files", []) if f.get("filename"))
