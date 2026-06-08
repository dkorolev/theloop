# Setting up theloop for Claude Code

One copy-paste terminal command installs the global **`/theloopify`** skill under `~/.claude/skills/`. That skill carries a shallow clone of [theloop](https://github.com/dkorolev/theloop) and, when you run it from a project repository in Claude Code, performs the full mechanical setup and then drives the one-time agentic **`/theloop-post-setuprepo`** step.

**Prerequisites:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code), `git`, and a fresh clone of the repository you want to instrument (one clone, one feature).

The installer shallow-clones [github.com/dkorolev/theloop](https://github.com/dkorolev/theloop) into `~/.claude/skills/theloopify/vendor/theloop/`. That upstream repository must contain `theloopify.sh`, `theloopify-install.py`, and the `.skills/` bundle.

## Copy and run (one time)

Paste this entire block into your terminal:

````bash
#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="${HOME}/.claude/skills/theloopify"
SCRIPTS_DIR="${SKILL_DIR}/scripts"
VENDOR_DIR="${SKILL_DIR}/vendor/theloop"
THELOOP_REPO="https://github.com/dkorolev/theloop"

echo "==> Installing theloopify Claude Code skill at ${SKILL_DIR}"

mkdir -p "${SCRIPTS_DIR}"

cat > "${SKILL_DIR}/SKILL.md" <<'EOF'
---
name: theloopify
description: >-
  Instruments the current repository with the theloop agent workflow. Runs the
  mechanical theloopify install from a bundled shallow clone of theloop, verifies
  the skill bundle landed, then executes the one-time agentic theloop-post-setuprepo
  skill to author PRECOMMIT.md and unlock the workflow skills. Use when setting up
  theloop in a client repository for the first time.
---

# theloopify

Set up the **discuss → issue → implement → PR** workflow in the repository you are working in.

This skill is fully contained in the target repository once the mechanical step finishes. Do not read or write files outside the target repository except to run the bundled `theloopify` script from your global skill directory.

## Parameters

This skill takes no parameters. If any are passed, stop immediately and report an error.

## Bundled theloop checkout

The mechanical installer lives at:

`~/.claude/skills/theloopify/vendor/theloop/theloopify`

If that path is missing, run `~/.claude/skills/theloopify/scripts/ensure-vendor.sh` once and retry.

## Steps

Work from the **repository root** you want to instrument (the current working directory unless the user explicitly named another path).

1. **Refuse the theloop repository itself.** If `.theloop/SKILLS-META-RULES.md` exists at the repository root, stop immediately: `theloopify` must target a separate client clone, not the theloop development repository.

2. **Detect prior runs.** Inspect these markers:
   - `.theloop/configure_the_loop.done` present → configuration already finished. Tell the user the repository is fully set up and they may use `/theloop-makeissue`, `/theloop-fixissue`, `/theloop-buildthis`, and `/theloop-precommit`. Stop successfully.
   - `.theloop/theloopified` present but `.theloop/configure_the_loop.done` absent → mechanical install already ran; skip to step 4.
   - neither marker present → continue with the mechanical install in step 3.

3. **Run the mechanical installer.** Execute:

   ```sh
   ~/.claude/skills/theloopify/scripts/run-theloopify.sh
   ```

   from the repository root (no arguments — it instruments the current directory).

   - If the script exits non-zero, stop immediately: report the error output and mark this skill as failed. Do not continue.
   - The script never commits; leave all scaffolding uncommitted.

4. **Verify the skill bundle.** Confirm every item below exists in the target repository:
   - `.theloop/theloopified`
   - `.theloop/must_run_configure_the_loop.txt`
   - `.theloop/skills/theloop-makeissue/SKILL.md`
   - `.theloop/skills/theloop-fixissue/SKILL.md`
   - `.theloop/skills/theloop-buildthis/SKILL.md`
   - `.theloop/skills/theloop-precommit/SKILL.md`
   - `.theloop/skills/theloop-post-setuprepo/SKILL.md`
   - `.claude/skills/theloop-post-setuprepo/SKILL.md` (symlink into `.theloop/skills/`)

   Optionally run the bundled verifier for a deterministic check:

   ```sh
   ~/.claude/skills/theloopify/scripts/verify-install.sh
   ```

   If verification fails, stop and report what is missing.

5. **Run the one-time agentic setup.** Read and follow **every step** of `.theloop/skills/theloop-post-setuprepo/SKILL.md` in this repository — that is `/theloop-post-setuprepo`. Do not skip steps or substitute your own summary.

   - If `theloop-post-setuprepo` fails or refuses preconditions, stop immediately and report the failure. This skill fails with it.
   - On success, `.theloop/configure_the_loop.done` must exist and `.theloop/must_run_configure_the_loop.txt` must be gone.

6. **Final report.** Tell the user:
   - theloop is fully configured in this repository;
   - the path to the `PRECOMMIT.md` that was written;
   - the workflow skills now available: `/theloop-makeissue`, `/theloop-fixissue <n>`, `/theloop-buildthis`, `/theloop-precommit`;
   - that `.theloop/` scaffolding and agent symlinks are local-only (listed in `.theloop/do_not_commit.txt`) and should not appear in feature pull requests.
EOF

cat > "${SCRIPTS_DIR}/ensure-vendor.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SKILL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="${SKILL_ROOT}/vendor/theloop"
REPO="https://github.com/dkorolev/theloop"
BRANCH="${THELOOP_VENDOR_BRANCH:-main}"

if [ -L "${VENDOR}" ]; then
  echo "error: ${VENDOR} is a symlink; remove it and re-run the installer" >&2
  exit 1
fi

if [ -d "${VENDOR}/.git" ]; then
  git -C "${VENDOR}" fetch --depth 1 origin "${BRANCH}"
  git -C "${VENDOR}" checkout -f "origin/${BRANCH}"
else
  mkdir -p "$(dirname "${VENDOR}")"
  git clone --depth 1 --branch "${BRANCH}" "${REPO}" "${VENDOR}"
fi

if [ ! -f "${VENDOR}/theloopify.sh" ] && [ ! -x "${VENDOR}/theloopify" ]; then
  echo "error: ${VENDOR} has no usable installer (neither theloopify.sh nor an executable theloopify) — publish theloop to ${REPO} first" >&2
  exit 1
fi
EOF
chmod +x "${SCRIPTS_DIR}/ensure-vendor.sh"

cat > "${SCRIPTS_DIR}/run-theloopify.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SKILL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="${SKILL_ROOT}/vendor/theloop"
"${SKILL_ROOT}/scripts/ensure-vendor.sh"
TARGET="${1:-$PWD}"
if [ -x "${VENDOR}/theloopify" ]; then
  exec "${VENDOR}/theloopify" "${TARGET}"
fi
exec "${VENDOR}/theloopify.sh" "${TARGET}"
EOF
chmod +x "${SCRIPTS_DIR}/run-theloopify.sh"

cat > "${SCRIPTS_DIR}/verify-install.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$PWD}"
fail() { echo "error: $1" >&2; exit 1; }
[ -f "${ROOT}/.theloop/theloopified" ] || fail "missing .theloop/theloopified"
[ -f "${ROOT}/.theloop/must_run_configure_the_loop.txt" ] || fail "missing .theloop/must_run_configure_the_loop.txt"
for skill in theloop-makeissue theloop-fixissue theloop-buildthis \
  InternalSkillCheckGhRepoAccessWithRunId theloop-precommit theloop-post-setuprepo \
  InternalSkillPreCommitForClientWithRunId; do
  [ -f "${ROOT}/.theloop/skills/${skill}/SKILL.md" ] || fail "missing .theloop/skills/${skill}/SKILL.md"
done
[ -L "${ROOT}/.claude/skills/theloop-post-setuprepo" ] || fail ".claude/skills/theloop-post-setuprepo is not a symlink"
[ -f "${ROOT}/.claude/skills/theloop-post-setuprepo/SKILL.md" ] || fail "theloop-post-setuprepo symlink does not resolve"
echo "theloop skill bundle verified in ${ROOT}"
EOF
chmod +x "${SCRIPTS_DIR}/verify-install.sh"

"${SCRIPTS_DIR}/ensure-vendor.sh"

echo "==> Done."
echo "    Skill:  ${SKILL_DIR}/SKILL.md"
echo "    Vendor: ${VENDOR_DIR} (shallow clone, refreshed on each install)"
echo ""
echo "Next: open Claude Code in a fresh clone of your project and run:"
echo "      /theloopify"
````

## What this script does

This is a one-time terminal installer. It puts a global **`/theloopify`** skill on your machine for Claude Code, bundles a shallow copy of the [theloop](https://github.com/dkorolev/theloop) repository inside that skill, and prints a reminder to run `/theloopify` from a project clone. It does **not** instrument your project repository itself — that happens later when you invoke the skill from Claude Code.

### Step by step

1. **Choose install locations.** It sets `~/.claude/skills/theloopify` as the skill directory, `~/.claude/skills/theloopify/scripts` for helper scripts, and `~/.claude/skills/theloopify/vendor/theloop` for the bundled theloop checkout.

2. **Write the global `/theloopify` skill.** It creates `~/.claude/skills/theloopify/SKILL.md`, which tells Claude Code how to instrument the repository you are working in: detect prior runs via `.theloop/theloopified` and `.theloop/configure_the_loop.done`, run the bundled mechanical `theloopify` installer when needed, verify the skill bundle landed, and then execute the one-time agentic `/theloop-post-setuprepo` skill installed into that repository.

3. **Write `ensure-vendor.sh`.** This helper shallow-clones `https://github.com/dkorolev/theloop` (branch `main`, overridable via `THELOOP_VENDOR_BRANCH`) into `vendor/theloop`, or refreshes that clone on re-run. It refuses a symlink at `vendor/theloop` and exits with an error if the checkout contains no usable installer — that is, when neither `theloopify.sh` nor an executable `theloopify` is present.

4. **Write `run-theloopify.sh`.** This helper calls `ensure-vendor.sh`, then runs the bundled `theloopify` (or `theloopify.sh`) against a target directory — defaulting to the current working directory when no argument is given.

5. **Write `verify-install.sh`.** This helper checks that a target repository has `.theloop/theloopified`, `.theloop/must_run_configure_the_loop.txt`, all seven bundled skills under `.theloop/skills/`, and a resolving `.claude/skills/theloop-post-setuprepo` symlink.

6. **Mark the helpers executable.** It runs `chmod +x` on all three scripts under `scripts/`.

7. **Fetch the bundled theloop checkout.** It runs `ensure-vendor.sh` immediately so the vendor tree exists before you open Claude Code.

8. **Print a short summary.** It echoes the skill and vendor paths and tells you to open Claude Code in a fresh project clone and run `/theloopify`.

## After installation

1. **Clone** the repository you want to work on (one clone, one feature).
2. **Start Claude Code** in that clone.
3. Run **`/theloopify`**.

The skill will:

- skip the mechanical step if `.theloop/theloopified` already exists;
- run the bundled `theloopify` script otherwise (it detects your GitHub remote, writes `.theloop/` scaffolding, copies the skill bundle, and symlinks it into `.claude/skills/`);
- verify the seven bundled skills are present;
- execute **`/theloop-post-setuprepo`** agentically (authors `PRECOMMIT.md`, flips the configuration gate).

When setup completes, use:

| Skill | Purpose |
|---|---|
| `/theloop-makeissue` | Capture a design discussion as a GitHub issue |
| `/theloop-fixissue <n>` | Implement an issue and open a pull request |
| `/theloop-buildthis` | Implement straight from the conversation |
| `/theloop-precommit` | Run pre-commit checks before committing |

## Re-running the installer

The terminal script is safe to run again. It refreshes `SKILL.md`, the helper scripts, and the shallow vendor clone under `~/.claude/skills/theloopify/vendor/theloop/`.

**Do not** run `/theloopify` a second time on the same clone after mechanical setup — `theloopify` refuses when `.theloop/theloopified` already exists. To start another feature, clone the repository again.

## How we know theloopify already ran

The mechanical script writes `.theloop/theloopified` as its final step and exits with an error if that file already exists. Full configuration is recorded separately in `.theloop/configure_the_loop.done` (written by `/theloop-post-setuprepo`).
