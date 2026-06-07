# Pre-commit checks

This file extends `PreCommitSkillWithRunId` with repository-specific checks beyond receipt hygiene, directory invariants, and skill validation. Each entry below becomes one `extra_checks` item in the pre-commit run receipt.

`.skills/PreCommitSkillWithRunId/scripts/precommit.py` runs every check listed in the YAML block.

```yaml
- check: example/code-pytest
  directory: example/code
  command: uv run pytest
```
