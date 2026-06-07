#!/usr/bin/env bash
#
# theloopify — instrument a freshly cloned client repository with the theloop
# agent workflow (discuss -> issue -> implement -> PR).
#
#   theloopify              # instrument the current working directory
#   theloopify /path/to/repo  # instrument that directory
#
# theloopify is mechanical and never commits: it copies the client skill bundle
# into .theloop/skills/, symlinks it into every supported coding-agent directory,
# and writes the .theloop/ scaffolding. The one-time, agentic /ConfigureTheLoop
# step (run afterwards) authors PRECOMMIT.md and unlocks the workflow skills.
#
# Designed to run exactly once per clone: one clone, one feature.
set -euo pipefail

# --- presentation -----------------------------------------------------------
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; CYAN=$'\033[36m'
  YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
else
  BOLD=; DIM=; GREEN=; CYAN=; YELLOW=; RED=; RESET=
fi
phase() { printf '%s==>%s %s%s%s\n' "$CYAN$BOLD" "$RESET" "$BOLD" "$1" "$RESET"; }
info()  { printf '    %s\n' "$1"; }
ok()    { printf '    %s%s%s\n' "$GREEN" "$1" "$RESET"; }
err()   { printf '%serror:%s %s\n' "$RED$BOLD" "$RESET" "$1" >&2; }
die()   { err "$1"; exit 1; }

# --- resolve the theloop checkout (this script's real directory) ------------
resolve() {
  t=$1
  while [ -L "$t" ]; do
    link=$(readlink "$t")
    case $link in
      /*) t=$link ;;
      *)  t=$(dirname "$t")/$link ;;
    esac
  done
  printf '%s/%s\n' "$(cd "$(dirname "$t")" && pwd)" "$(basename "$t")"
}
SELF=$(resolve "$0")
THELOOP_ROOT=$(dirname "$SELF")

# --- 1. resolve the target; refuse the theloop repo itself ------------------
if [ "$#" -gt 1 ]; then
  die "too many arguments; usage: theloopify [TARGET_DIR]"
fi
RAW_TARGET=${1:-$PWD}
[ -d "$RAW_TARGET" ] || die "target directory does not exist: $RAW_TARGET"
TARGET=$(cd "$RAW_TARGET" && pwd)

phase "theloop — instrumenting a client repository"
info "${DIM}theloop checkout:${RESET} $THELOOP_ROOT"
info "${DIM}target repo:     ${RESET} $TARGET"

if [ -f "$TARGET/.theloop/SKILLS-META-RULES.md" ] || [ "$TARGET" = "$THELOOP_ROOT" ]; then
  die "refusing to instrument the theloop repository itself; run theloopify against a separate client clone"
fi

# --- 2. refuse a second run -------------------------------------------------
if [ -e "$TARGET/.theloop/theloopified" ]; then
  err "$TARGET is already theloopified."
  info "theloopify instruments a freshly cloned repo, dedicated to a single feature."
  info "To start another feature, clone the repository again and run theloopify on the new clone."
  exit 1
fi

# --- 3. verify the target is a git repository -------------------------------
git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1 || die "$TARGET is not a git repository"

# --- 4. detect (or ask for) the GitHub remote ------------------------------
phase "Detecting the GitHub remote"
mkdir -p "$TARGET/.theloop"
REPO_URL=""
for r in $(git -C "$TARGET" remote 2>/dev/null || true); do
  url=$(git -C "$TARGET" remote get-url "$r" 2>/dev/null || true)
  case $url in
    *github.com*) REPO_URL=$url; break ;;
  esac
done
if [ -n "$REPO_URL" ]; then
  ok "found GitHub remote: $REPO_URL"
elif [ -t 0 ]; then
  printf '    %sNo GitHub remote found.%s Enter the GitHub repository URL: ' "$YELLOW" "$RESET"
  read -r REPO_URL
  [ -n "$REPO_URL" ] || die "no repository URL provided"
else
  die "no GitHub remote found and not running interactively; add a GitHub remote or run theloopify in a terminal"
fi
printf '%s\n' "$REPO_URL" > "$TARGET/.theloop/repo.txt"

# --- 5. ensure tmp/ is gitignored ------------------------------------------
GI="$TARGET/.gitignore"
if [ ! -f "$GI" ] || ! grep -qxF 'tmp/' "$GI"; then
  if [ -f "$GI" ] && [ -n "$(tail -c1 "$GI" 2>/dev/null)" ]; then printf '\n' >> "$GI"; fi
  printf 'tmp/\n' >> "$GI"
  info "added tmp/ to .gitignore"
fi

# --- 6. write the .theloop/ scaffolding ------------------------------------
phase "Writing .theloop/ scaffolding"
cat > "$TARGET/.theloop/do_not_commit.txt" <<'EOF'
.theloop/
.cursor/skills/
.claude/skills/
.codex/skills/
.agents/skills/
tmp/
EOF
printf 'Run /ConfigureTheLoop to finish setting up theloop in this repository.\n' \
  > "$TARGET/.theloop/must_run_configure_the_loop.txt"
ok "wrote repo.txt, do_not_commit.txt, must_run_configure_the_loop.txt"

# --- 7/8/9. copy + rewrite + rename the skills, then symlink them -----------
phase "Installing the skill bundle"
SUMMARY=$("$THELOOP_ROOT/theloopify-install.py" "$THELOOP_ROOT" "$TARGET")
COUNT=$(printf '%s' "$SUMMARY" | grep -c '\.theloop/skills/' || true)
ok "copied skills into .theloop/skills/ and symlinked them into .cursor, .claude, .codex, .agents"

# --- 10. mark instrumented (last, so a failed run stays retryable) ----------
printf 'theloopified: %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" > "$TARGET/.theloop/theloopified"

# --- summary ----------------------------------------------------------------
printf '\n'
phase "Done"
info "${GREEN}theloop is installed${RESET} in $TARGET (all changes left uncommitted)."
info ""
info "${BOLD}Next step:${RESET} run ${CYAN}/ConfigureTheLoop${RESET} in your coding agent to author"
info "PRECOMMIT.md and unlock the workflow skills:"
info "  ${DIM}/IssueWhatWeJustDiscussed, /MakePRForIssue <n>, /ImplementWhatWeJustDiscussed, /PreCommitSkill${RESET}"
info ""
info "Review the uncommitted changes; the .theloop/ scaffolding and agent symlinks"
info "are local-only (listed in .theloop/do_not_commit.txt) and never enter feature PRs."
