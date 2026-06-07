# Visualization and Topology

This file lives at `.theloop/VIZ.md`, under the `.theloop/` directory in the root of the repo. It contains exactly the full list of the skills in this repository and a complete list of what skill can invoke what other skill: every skill and every invocation relationship in the repo is listed here, and everything listed here is actually present in the repo.

## Skills

| Skill | Description |
|---|---|
| [`InternalSkillValidateSkill`](../.skills/InternalSkillValidateSkill/SKILL.md) | Meta-skill that validates another skill in this repository against `.theloop/SKILLS-META-RULES.md`. |
| [`InternalSkillValidateAllSkills`](../.skills/InternalSkillValidateAllSkills/SKILL.md) | Meta-skill that validates every skill in this repository against `.theloop/SKILLS-META-RULES.md`, by fanning out subagents to invoke `InternalSkillValidateSkill` once per skill and then performing the whole-repo checks. |
| [`InternalSkillCheckSingleRuleWithRunId`](../.skills/InternalSkillCheckSingleRuleWithRunId/SKILL.md) | Meta-skill that checks a single directory rule against its scoped files, with caching per `.theloop/CACHING.md`. |
| [`InternalSkillCheckAllRulesWithRunId`](../.skills/InternalSkillCheckAllRulesWithRunId/SKILL.md) | Meta-skill that checks all directory rules listed in `ai-rules.yml` by fanning out subagents to invoke `InternalSkillCheckSingleRuleWithRunId` once per rule. |
| [`InternalSkillPreCommitSkillWithRunId`](../.skills/InternalSkillPreCommitSkillWithRunId/SKILL.md) | Meta-skill that performs the pre-commit gate under a caller-supplied `SkillRunId`: receipt-hygiene checks, directory rules via `InternalSkillCheckAllRulesWithRunId`, optional `PRECOMMIT.md` checks, then `InternalSkillValidateAllSkills` for full compliance. |
| [`PreCommitSkill`](../.skills/PreCommitSkill/SKILL.md) | Meta-skill that gates a commit to this repository: takes no parameters, generates a fresh `SkillRunId` in the default format, and delegates to `InternalSkillPreCommitSkillWithRunId`. |
| [`ImplementWhatWeJustDiscussed`](../.skills/ImplementWhatWeJustDiscussed/SKILL.md) | Summarizes the current conversation to extract the feature request, implements the feature with a design document, then invokes `PreCommitSkill` and iterates on any failures until all pre-commit checks pass. |
| [`InternalSkillCheckGhRepoAccessWithRunId`](../.skills/InternalSkillCheckGhRepoAccessWithRunId/SKILL.md) | Checks that the GitHub CLI (`gh`) is installed, authenticated, and can access the repository URL in `.theloop/repo.txt`, ensures Issues are enabled on the repository, and ensures the `theloop` label exists for bugs and pull requests. |
| [`IssueWhatWeJustDiscussed`](../.skills/IssueWhatWeJustDiscussed/SKILL.md) | Summarizes the current conversation into a feature specification, clarifies with the human until the picture is clear, then creates a GitHub issue tagged with `theloop`. |
| [`MakePRForIssue`](../.skills/MakePRForIssue/SKILL.md) | Implements a GitHub issue as a pull request: unique branch, feature implementation, `PreCommitSkill`, commit, `theloop`-labeled PR, and issue journal comments. |

## SkillInvocations

| Invoker | Invokee |
|---|---|
| `PreCommitSkill` | `InternalSkillPreCommitSkillWithRunId` |
| `InternalSkillPreCommitSkillWithRunId` | `InternalSkillCheckAllRulesWithRunId` |
| `InternalSkillPreCommitSkillWithRunId` | `InternalSkillValidateAllSkills` |
| `InternalSkillCheckAllRulesWithRunId` | `InternalSkillCheckSingleRuleWithRunId` |
| `InternalSkillValidateAllSkills` | `InternalSkillValidateSkill` |
| `ImplementWhatWeJustDiscussed` | `PreCommitSkill` |
| `IssueWhatWeJustDiscussed` | `InternalSkillCheckGhRepoAccessWithRunId` |
| `MakePRForIssue` | `InternalSkillCheckGhRepoAccessWithRunId` |
| `MakePRForIssue` | `PreCommitSkill` |

## Diagram

An arrow from A to B means skill A can, under some circumstances, invoke skill B.

```mermaid
graph TD
    InternalSkillCheckGhRepoAccessWithRunId["InternalSkillCheckGhRepoAccessWithRunId"]
    IssueWhatWeJustDiscussed["IssueWhatWeJustDiscussed"] --> InternalSkillCheckGhRepoAccessWithRunId
    MakePRForIssue["MakePRForIssue"] --> InternalSkillCheckGhRepoAccessWithRunId
    MakePRForIssue --> PreCommitSkill["PreCommitSkill"]
    ImplementWhatWeJustDiscussed["ImplementWhatWeJustDiscussed"] --> PreCommitSkill["PreCommitSkill"]
    PreCommitSkill --> InternalSkillPreCommitSkillWithRunId["InternalSkillPreCommitSkillWithRunId"]
    InternalSkillPreCommitSkillWithRunId --> InternalSkillCheckAllRulesWithRunId["InternalSkillCheckAllRulesWithRunId"]
    InternalSkillPreCommitSkillWithRunId --> InternalSkillValidateAllSkills["InternalSkillValidateAllSkills"]
    InternalSkillCheckAllRulesWithRunId --> InternalSkillCheckSingleRuleWithRunId["InternalSkillCheckSingleRuleWithRunId"]
    InternalSkillValidateAllSkills --> InternalSkillValidateSkill["InternalSkillValidateSkill"]
```
