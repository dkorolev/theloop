# Skills

This file contains exactly the full list of the skills in this repository: every skill in the repo is listed here, and every skill listed here is present in the repo.

| Skill | Description |
|---|---|
| [`ValidateSkill`](.skills/ValidateSkill/SKILL.md) | Meta-skill that validates another skill in this repository against `RULES.md`. Takes a `SkillRunId` and the name of the skill to check; errors if the target skill does not exist, otherwise reports whether it complies with every rule. |
| [`ValidateAllSkills`](.skills/ValidateAllSkills/SKILL.md) | Meta-skill that validates every skill in this repository against `RULES.md`. Takes a single `SkillRunId`; invokes `ValidateSkill` once per skill, then performs the whole-repo checks that `SKILLS.md` and `VIZ.md` exactly match the repository. |
| [`PreCommitSkill`](.skills/PreCommitSkill/SKILL.md) | Meta-skill that gates a commit to this repository. Takes no parameters, generating a random run identifier instead; checks that the `tmp/` directory is gitignored and that no run receipts are tracked or staged, performs every additional check described in `PRECOMMIT.md` when that file exists at the root of the repo, then invokes `ValidateAllSkills` to confirm that every skill and the repository as a whole comply with `RULES.md`. |
