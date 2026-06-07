# Pre-commit checks

This file extends `InternalSkillPreCommitSkillWithRunId` with repository-specific checks beyond receipt hygiene, directory rules, and skill validation. Each entry below becomes one `extra_checks` item in the pre-commit run receipt.

`.skills/InternalSkillPreCommitSkillWithRunId/scripts/precommit.py` runs every check listed in the YAML block.

```yaml
- check: internal-skill-naming
  directory: .
  command: .skills/InternalSkillPreCommitSkillWithRunId/scripts/internal-skill-names.py
- check: example/code-pytest
  directory: example/code
  command: uv run pytest
```
