# Pre-commit checks

This file extends `theloop-internal-precommit` with repository-specific checks beyond receipt hygiene, directory rules, and skill validation. Each entry below becomes one `extra_checks` item in the pre-commit run receipt.

`.skills/theloop-internal-precommit/scripts/precommit.py --list` parses the YAML block into a check list; the skill then fans out one subagent per check and runs them in parallel, each invoking `precommit.py --checks-file <one-check>` to run its single check. The parallelism lives in the skill prompt, not in the script.

```yaml
- check: internal-skill-naming
  directory: .
  command: .skills/theloop-internal-precommit/scripts/internal-skill-names.py
- check: example/code-pytest
  directory: example/code
  command: uv run pytest
- check: theloopify-smoke-test
  directory: .
  command: ./theloopify-test.sh
```
