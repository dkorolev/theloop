#!/usr/bin/env bash
#
# theloopify-test.sh — a deterministic smoke test for theloopify.
#
# It instruments a throwaway git repository created under tmp/ (gitignored, inside
# this repo) and asserts the resulting layout: the .theloop/ scaffolding, the
# copied skill bundle with install-name renames and path rewriting applied, the
# agent symlinks, the absence of a client-root .skills/, refusal of a second run,
# and refusal to instrument the theloop repo itself.
#
# Run from the repository root:  ./theloopify-test.sh
set -euo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/tmp/theloopify-smoke-test"
FAILED=0

fail() { printf 'FAIL: %s\n' "$1" >&2; FAILED=1; }
have() { [ -e "$1" ] || fail "expected to exist: ${1#"$WORK"/}"; }
missing() { [ ! -e "$1" ] && return 0; fail "expected NOT to exist: ${1#"$WORK"/}"; }
contains() { grep -qF "$2" "$1" || fail "expected $1 to contain: $2"; }
absent() { grep -qF "$2" "$1" && fail "expected $1 to NOT contain: $2" || true; }

# --- fresh throwaway client repo with a GitHub remote (no interactive prompt) ---
rm -rf "$WORK"
mkdir -p "$WORK"
git -C "$WORK" init -q
git -C "$WORK" remote add origin "https://github.com/example/client.git"
printf '# client\n' > "$WORK/README.md"

# --- run theloopify against it ---------------------------------------------
"$ROOT/theloopify.sh" "$WORK" >/dev/null || fail "theloopify exited non-zero on a fresh repo"

# --- scaffolding ------------------------------------------------------------
have "$WORK/.theloop/theloopified"
have "$WORK/.theloop/must_run_configure_the_loop.txt"
have "$WORK/.theloop/do_not_commit.txt"
contains "$WORK/.theloop/repo.txt" "github.com/example/client"
contains "$WORK/.theloop/do_not_commit.txt" ".theloop/"
contains "$WORK/.theloop/do_not_commit.txt" "tmp/"
contains "$WORK/.gitignore" "tmp/"
# Deliberate compromise: theloopify gitignores every path it instruments so the
# working tree stays clean, and excludes the .gitignore change itself from commits.
for p in ".theloop/" ".cursor/skills/" ".claude/skills/" ".codex/skills/" ".agents/skills/"; do
  contains "$WORK/.gitignore" "$p"
done
contains "$WORK/.theloop/do_not_commit.txt" ".gitignore"
# the instrumentation must actually be hidden from a dirty-tree check:
git -C "$WORK" status --porcelain | grep -qE '(\.theloop/|/skills/)' \
  && fail "theloop instrumentation is visible to git status (should be gitignored)" || true
# PRECOMMIT.md is owned by newrepo-theloopify-internal-postinit, not theloopify:
missing "$WORK/PRECOMMIT.md"

# --- the eight bundled skills, under client-facing names --------------------
for s in theloop-makeissue theloop-fixissue theloop-buildthis theloop-keep-maxims-up-to-date \
         InternalSkillCheckGhRepoAccessWithRunId theloop-precommit newrepo-theloopify-internal-postinit \
         InternalSkillPreCommitForClientWithRunId; do
  have "$WORK/.theloop/skills/$s/SKILL.md"
done
# the *ForClientRepos development names must NOT appear as client directories:
missing "$WORK/.theloop/skills/PreCommitSkillForClientRepos"
missing "$WORK/.theloop/skills/ConfigureTheLoopForClientRepos"
# meta-skills are not installed:
missing "$WORK/.theloop/skills/InternalSkillValidateAllSkills"
missing "$WORK/.theloop/skills/InternalSkillPreCommitSkillWithRunId"
# no .skills/ at the client root:
missing "$WORK/.skills"

# --- install-name renames inside the copied files --------------------------
contains "$WORK/.theloop/skills/theloop-precommit/SKILL.md" "name: theloop-precommit"
absent   "$WORK/.theloop/skills/theloop-precommit/SKILL.md" "ForClientRepos"
contains "$WORK/.theloop/skills/newrepo-theloopify-internal-postinit/SKILL.md" "name: newrepo-theloopify-internal-postinit"
absent   "$WORK/.theloop/skills/newrepo-theloopify-internal-postinit/SKILL.md" "ForClientRepos"
contains "$WORK/.theloop/skills/newrepo-theloopify-internal-postinit/scripts/write-receipt.py" 'SKILL = "newrepo-theloopify-internal-postinit"'

# --- path rewriting: .skills/ -> .theloop/skills/ everywhere ----------------
if grep -rIl '\.skills/' "$WORK/.theloop/skills" >/dev/null 2>&1; then
  fail "copied skills still reference .skills/ (should be .theloop/skills/)"
fi
contains "$WORK/.theloop/skills/theloop-fixissue/SKILL.md" ".theloop/skills/theloop-fixissue/scripts/"

# --- agent symlinks ---------------------------------------------------------
for agent in .cursor .claude .codex .agents; do
  link="$WORK/$agent/skills/theloop-fixissue"
  [ -L "$link" ] || fail "$agent/skills/theloop-fixissue is not a symlink"
  [ -f "$link/SKILL.md" ] || fail "$agent/skills/theloop-fixissue does not resolve to a skill"
done

# --- idempotency: a second run must fail ------------------------------------
if "$ROOT/theloopify.sh" "$WORK" >/dev/null 2>&1; then
  fail "theloopify did not refuse a second run"
fi

# --- it must refuse to instrument the theloop repo itself -------------------
if "$ROOT/theloopify.sh" "$ROOT" >/dev/null 2>&1; then
  fail "theloopify did not refuse to instrument the theloop repo itself"
fi
missing "$ROOT/.theloop/theloopified"  # the theloop repo must be untouched

# --- cleanup ----------------------------------------------------------------
rm -rf "$WORK"

if [ "$FAILED" -eq 0 ]; then
  echo "theloopify smoke test passed"
  exit 0
fi
echo "theloopify smoke test FAILED"
exit 1
