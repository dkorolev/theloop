#!/usr/bin/env python3
"""Parse, scope, probe, and cache directory rules, per .theloop/RULE-FILES.md.

Usage: .skills/InternalSkillCheckSingleRuleWithRunId/scripts/rules.py parse <path-to-rule.yml>
       .skills/InternalSkillCheckSingleRuleWithRunId/scripts/rules.py probe-one <path-to-rule.yml>
       .skills/InternalSkillCheckSingleRuleWithRunId/scripts/rules.py write <path-to-rule.yml>
"""
import hashlib
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    yaml = None

CACHE_DIR = os.path.join("tmp", "caches")
ALLOWED_TOP_LEVEL = {"rule", "use", "exclude"}


def die_json(error, code=2):
    print(json.dumps({"error": error}))
    return code


def non_ignored_files(pathspec=None):
    cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    if pathspec is not None:
        cmd += ["--", pathspec]
    try:
        listed = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120).stdout.splitlines()
    except subprocess.TimeoutExpired:
        sys.exit(die_json("timeout: git ls-files exceeded 120s"))
    return sorted(p for p in set(listed) if os.path.isfile(p))


def discover_rules():
    return [p for p in non_ignored_files() if p.endswith("-rule.yml")]


def rule_directory(rule_path):
    directory = os.path.dirname(rule_path)
    return directory if directory else "."


def normalize_entry(entry):
    if not isinstance(entry, str) or not entry.strip():
        raise ValueError("scope list entries must be non-empty strings")
    entry = entry.strip()
    if entry.startswith("/"):
        raise ValueError(f"scope path must be relative to the rule directory, not absolute: {entry!r}")
    if ".." in entry.split("/"):
        raise ValueError(f"scope path must not escape the rule directory: {entry!r}")
    return entry.rstrip("/")


def translate_component(component):
    out = []
    for ch in component:
        if ch == "*":
            out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(ch))
    return "".join(out)


def compile_glob(entry):
    components = entry.split("/")
    regex = ""
    for i, component in enumerate(components):
        last = i == len(components) - 1
        if component == "**":
            if last:
                regex = (regex[:-1] + "(?:/.*)?") if regex else ".+"
            else:
                regex += "(?:[^/]+/)*"
        else:
            regex += translate_component(component)
            if not last:
                regex += "/"
    return re.compile(regex + r"\Z")


def expand_entry(entry, rule_dir, subtree_files):
    if "*" in entry or "?" in entry:
        pattern = compile_glob(entry)
        prefix = "" if rule_dir == "." else rule_dir + os.sep
        matched = [p for p in subtree_files if p.startswith(prefix) and pattern.match(p[len(prefix):])]
        if not matched:
            raise ValueError(f"glob pattern matches no files: {entry!r}")
        return matched
    full = os.path.normpath(os.path.join(rule_dir, entry))
    if rule_dir == ".":
        if os.path.isabs(full) or full == ".." or full.startswith("../"):
            raise ValueError(f"scope path must stay within the rule directory: {entry!r}")
    else:
        prefix = rule_dir + os.sep
        if full != rule_dir and not full.startswith(prefix):
            raise ValueError(f"scope path must stay within the rule directory: {entry!r}")
    if os.path.isdir(full):
        return [p for p in subtree_files if p == full or p.startswith(full + "/")]
    if os.path.isfile(full):
        return [full] if full in subtree_files else []
    raise ValueError(f"scope path does not exist: {entry!r}")


def parse_rule_file(rule_path):
    if yaml is None:
        raise ValueError("PyYAML is required to parse rule files but is not installed")
    try:
        with open(rule_path) as f:
            doc = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {rule_path}: {exc}") from exc
    if doc is None:
        raise ValueError(f"{rule_path}: file is empty")
    if not isinstance(doc, dict):
        raise ValueError(f"{rule_path}: root must be a YAML mapping")
    extra = set(doc) - ALLOWED_TOP_LEVEL
    if extra:
        raise ValueError(f"{rule_path}: unknown top-level key(s): {', '.join(sorted(extra))}")
    rule_text = doc.get("rule")
    if not isinstance(rule_text, str) or not rule_text.strip():
        raise ValueError(f"{rule_path}: required key 'rule' must be a non-empty string")
    has_use = "use" in doc
    has_exclude = "exclude" in doc
    if has_use and has_exclude:
        raise ValueError(f"{rule_path}: 'use' and 'exclude' are mutually exclusive")
    rule_dir = rule_directory(rule_path)
    subtree_files = non_ignored_files(rule_dir)
    if has_use:
        entries = doc["use"] or []
        if not isinstance(entries, list):
            raise ValueError(f"{rule_path}: 'use' must be a list")
        scoped = set()
        for raw in entries:
            for path in expand_entry(normalize_entry(raw), rule_dir, subtree_files):
                scoped.add(path)
        scoped.add(rule_path)
    elif has_exclude:
        entries = doc["exclude"] or []
        if not isinstance(entries, list):
            raise ValueError(f"{rule_path}: 'exclude' must be a list")
        excluded = set()
        for raw in entries:
            for path in expand_entry(normalize_entry(raw), rule_dir, subtree_files):
                excluded.add(path)
        scoped = set(subtree_files) - excluded
        scoped.add(rule_path)
    else:
        scoped = set(subtree_files)
        scoped.add(rule_path)
    return {
        "rule": rule_path,
        "rule_text": rule_text,
        "directory": rule_dir,
        "scope_files": sorted(scoped),
    }


def fingerprint_of(rule_path, scope_files):
    check = f"rule:{rule_path}"
    lines = [f"{hashlib.sha256(open(p, 'rb').read()).hexdigest()}  {p}" for p in scope_files]
    manifest = f"check: {check}\n" + "".join(line + "\n" for line in lines)
    return check, hashlib.sha256(manifest.encode("utf-8")).hexdigest(), lines


def cmd_parse(rule_path):
    try:
        parsed = parse_rule_file(rule_path)
    except ValueError as exc:
        print(json.dumps({"status": "fail", "detail": str(exc)}))
        return 1
    print(json.dumps({"status": "pass", **parsed}, indent=2))
    return 0


def cmd_probe_one(rule_path):
    actual = discover_rules()
    if rule_path not in actual:
        return die_json(f"{rule_path} is not a non-ignored *-rule.yml file of this repository")
    try:
        parsed = parse_rule_file(rule_path)
    except ValueError as exc:
        print(json.dumps({"rule": rule_path, "parse_status": "fail", "detail": str(exc), "cached": False}, indent=2))
        return 0
    _, fingerprint, _ = fingerprint_of(rule_path, parsed["scope_files"])
    cache_path = os.path.join(CACHE_DIR, fingerprint + ".txt")
    print(json.dumps({
        "rule": rule_path,
        "parse_status": "pass",
        "scope_files": parsed["scope_files"],
        "cached": os.path.isfile(cache_path),
        "cache_path": cache_path,
        "fingerprint": fingerprint,
    }, indent=2))
    return 0


def cmd_write(rule_path):
    actual = discover_rules()
    if rule_path not in actual:
        return die_json(f"{rule_path} is not a non-ignored *-rule.yml file of this repository")
    parsed = parse_rule_file(rule_path)
    check, fingerprint, lines = fingerprint_of(rule_path, parsed["scope_files"])
    cache_path = os.path.join(CACHE_DIR, fingerprint + ".txt")
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.isfile(cache_path):
        with open(cache_path, "w") as f:
            f.write(f"check: {check}\nverdict: pass\nfiles:\n" + "".join(line + "\n" for line in lines))
    print(cache_path)
    return 0


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("parse", "probe-one", "write"):
        return die_json("usage: rules.py parse|probe-one|write <path-to-rule.yml>")
    command, rule_path = sys.argv[1], sys.argv[2]
    if command == "parse":
        return cmd_parse(rule_path)
    if command == "probe-one":
        return cmd_probe_one(rule_path)
    return cmd_write(rule_path)


if __name__ == "__main__":
    sys.exit(main())
