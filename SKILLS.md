# Skills

This file contains exactly the full list of the skills in this repository: every skill in the repo is listed here, and every skill listed here is present in the repo.

| Skill | Description |
|---|---|
| [`ValidateSkill`](.skills/ValidateSkill/SKILL.md) | Meta-skill that validates another skill in this repository against `.ai/RULES.md`. Takes a `SkillRunId` and the name of the skill to check; errors if the target skill does not exist, otherwise reports whether it complies with every rule. |
| [`ValidateAllSkills`](.skills/ValidateAllSkills/SKILL.md) | Meta-skill that validates every skill in this repository against `.ai/RULES.md`. Takes a single `SkillRunId`; invokes `ValidateSkill` once per skill in parallel, then performs the whole-repo checks that `SKILLS.md` and `.ai/VIZ.md` exactly match the repository. |
| [`PreCommitSkillWithRunId`](.skills/PreCommitSkillWithRunId/SKILL.md) | Meta-skill that performs the pre-commit gate for this repository under a caller-supplied run identifier. Takes a single `SkillRunId`; checks receipt hygiene, probes and runs the directory invariants listed in `ai-invariants.yml` (stale ones in parallel, cached ones skipped per `.ai/CACHING.md`), performs every additional check described in `PRECOMMIT.md` when that file exists, then invokes `ValidateAllSkills` to confirm that every skill and the repository as a whole comply with `.ai/RULES.md`. |
| [`PreCommitSkill`](.skills/PreCommitSkill/SKILL.md) | Meta-skill that gates a commit to this repository. Takes no parameters and errors if any are passed; generates a fresh `SkillRunId` in the default format codified in `.ai/RULES.md` and delegates the entire pre-commit gate to `PreCommitSkillWithRunId` under that identifier. |
