#!/usr/bin/env python3
"""Upsert one maxim, or a list of maxims, into its category's .yml source of truth,
then regenerate that category's .md from it.

Usage (from the repository root):
  record-maxim.py --run-id SKILL_RUN_ID [--input FILE]     # else reads stdin

Reads a maxim JSON object, or a JSON list of them. The .yml file is the single source
of truth; this script always updates the .yml first and immediately regenerates the
.md from it. The .md is never hand-edited and carries no per-maxim markers. A maxim is
keyed by an id derived from its title alone, so re-recording refines it in place
rather than duplicating it, and a category move never changes the id.

Output: a JSON summary on stdout.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import argparse
import json
import os
import sys

from common import (
    die, MAXIMS_DIR, slug, maxim_id, category_yml, category_md, category_title,
    require_ready, load_category, load_category_text, dump_category, render_md,
    create_new, cas_update, write_text_atomic, update_metadata, dumps,
)

VALID_STATUS = {"proposed", "confirmed", "superseded"}


def normalize(m):
    for field in ("category", "title", "statement"):
        if not isinstance(m.get(field), str) or not m[field].strip():
            die(f"each maxim needs a non-empty string '{field}'")
    status = m.get("status", "proposed")
    if status not in VALID_STATUS:
        die(f"status must be one of {sorted(VALID_STATUS)}; got '{status}'")
    entry = {"id": maxim_id(m["title"]), "title": m["title"].strip(),
             "statement": m["statement"].strip(), "status": status}
    if m.get("rationale"):
        entry["rationale"] = m["rationale"].strip()
    if m.get("applies_to"):
        entry["applies_to"] = list(m["applies_to"])
    if m.get("evidence"):
        entry["evidence"] = m["evidence"]
    return entry


def upsert(cat, entry, cid, title):
    cat.setdefault("category", cid)
    cat.setdefault("title", title)
    cat.setdefault("maxims", [])
    for i, ex in enumerate(cat["maxims"]):
        if ex.get("id") == entry["id"]:
            cat["maxims"][i] = entry
            return
    cat["maxims"].append(entry)


def record_one(m, run_id):
    cid = slug(m["category"])
    entry = normalize(m)
    mid = entry["id"]
    title = category_title(cid)
    yml_name, md_name = category_yml(cid), category_md(cid)
    yml_path = os.path.join(MAXIMS_DIR, yml_name)
    md_path = os.path.join(MAXIMS_DIR, md_name)

    # action label from a pre-read (best-effort; the CAS handles correctness)
    if not os.path.exists(yml_path):
        action = "created"
    else:
        prior = next((x for x in load_category(yml_path).get("maxims", []) if x.get("id") == mid), None)
        action = "unchanged" if prior == entry else ("updated" if prior else "added")

    # 1) update the .yml source of truth — upsert by id, re-applied to fresh content
    def transform(old_text):
        cat = load_category_text(old_text)
        upsert(cat, entry, cid, cat.get("title") or title)
        return dump_category(cat)

    if not os.path.exists(yml_path):
        try:
            create_new(yml_path, dump_category({"category": cid, "title": title, "maxims": [entry]}))
        except FileExistsError:
            cas_update(yml_path, transform, run_id)
    else:
        cas_update(yml_path, transform, run_id)

    # 2) regenerate the .md from the committed .yml — write only when it changes
    new_md = render_md(load_category(yml_path))
    if not os.path.exists(md_path) or open(md_path, encoding="utf-8").read() != new_md:
        write_text_atomic(md_path, new_md, run_id)

    # 3) register the category file in metadata (sorted, deduped)
    def index(meta):
        cats = meta.setdefault("categories", [])
        if yml_name not in cats:
            cats.append(yml_name)
            cats.sort()
    update_metadata(index, run_id)
    return {"id": mid, "category": cid, "yml": yml_name, "md": md_name,
            "status": entry["status"], "action": action}


def load_input(args):
    raw = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"input is not valid JSON: {exc}")
    return data if isinstance(data, list) else [data]


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input")
    args = parser.parse_args()
    require_ready()

    maxims = load_input(args)
    if not maxims:
        die("no maxims provided")
    if not all(isinstance(m, dict) for m in maxims):
        die("input must be a maxim object or a JSON list of maxim objects")

    recorded = [record_one(m, args.run_id) for m in maxims]
    print(dumps({"recorded": recorded}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
