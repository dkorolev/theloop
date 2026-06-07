# Rules for Skills

Every skill in this repository must comply with all of the rules below. The `ValidateSkill` skill checks compliance. The `ValidateAllSkills` skill checks compliance of all skills.

## Rule 1: Contained withint the repo

Every skill should mention that running the skill is an operation that is fully contained within the directory of the reposirory. The agentic runner of the skill should not need to access files outside the reposirory, and it should not attempt to access files outside the repository.

## Rule 2: Strict with parameters

Every skill should have strict run semantics, such as "this skill takes two arguments, the `SkillRunId` and the `OtherSkillName`. Prior to executing itself, every skill must check that the parameters are correctly passed along.

Moreover, validation should take place beyond the number of parameters. For instance, the skill should instruct the runner that for a given `SkillRunId`, no `tmp/${SkillRunId}.json` file should exist in the repository, and for the 

Furthermore, when a skill is executing other skills, it should make sure to pass just the right parameters, in the right quantity and order.

## Rule 3: Strict with output in the form of Run Receipts

Most skills must take the `SkillRunId` as the first parameter. The skills that do not require this parameter should explicitly state so in their body, that this is the exceptional one that does not require the `SkillRunId` parameter.

For skills with the `SkillRunId` parameter, the skill should explicitly mention several things:

* The skill should refuse to run, and result in an error, if the `tmp/${SkillRunId}.json` file exists prior to the skill being run.
* Except the very error that the `tmp/${SkillRunId}.json` file exists prior to running the skill, running the skill, no matter whether it results in success or in error, must produce the `tmp/${SkillRunId}.json` file, in addition to providing English-first output.
* The resulting `tmp/${SkillRunId}.json` receipt file should be of fixed schema, which is either `{"error":"..."}`, or other valid schemas provided exhaustively in the definition of the skill.

Specifically, for every skill that does take the `SkillRunId` as the parameter, the very rule to write but not overwrite the `tmp/${SkillRunId}.json` file must be present in the skill definition at least twice: once closer to the beginning of the skill, and one towards the very end of it.

Concretely, a skill complies with this rule when all of the following hold:

1. The skill declares `SkillRunId` as one of its parameters.
2. The first instruction of the skill body tells the model to write `tmp/<SkillRunId>.json` upon completion.
3. The last instruction of the skill body repeats that same requirement.
4. The skill describes the JSON schema of the object that goes into `tmp/<SkillRunId>.json`.

Note that the `tmp/` directory is `.gitignore`-d, so skill run receipts are never committed. The `PreCommitSkill` skill must check this.

# Rule 4: Universal directory for skills

The skills live under the `.skills/` directory in the root of the repo.

# Rule 5: The `SKILLS.md` file should be up to date

The `SKILLS.md` file should, at any commit in this repo, contain exactly the full list of the skills.

"The full list" here means that every skill in the repo must be present in `SKILLS.md`, and every skill present in `SKILLS.md` is present in the repo. Same with invocation relationships: every invocation relationship between two skills must be present in `VIZ.md`, and every relation that is listed in `VIZ.md` must be actual in the repo.

# Rule 6: Visualization and topology

The `VIZ.md` file should, at any commit in this repo, contain exactly the full list of the skills, and a complete list of what skill can invoke what other skill.

"The full list" here means that every skill in the repo must be present in `VIZ.md`, and every skill present in `VIZ.md` is present in the repo. Same with invocation relationships: every invocation relationship between two skills must be present in `VIZ.md`, and every relation that is listed in `VIZ.md` must be actual in the repo.

Besides the textual list (two markdown tables, Skills and SkillInvocations), the `VIZ.md` file should also contain a Mermaid diagram outlining the above graphically: skills as nodes, skill invocation relationships as arrows, where an arrow from A to B means skill A can, under some circumstances, invoke skill B.

# Rule 7: Use of scripts

It is undesirable that skills write temporary Python files to run themselves. If a skill may need to execute a piece of code that is non-trivial, the skill should provide the respective scripts under `.skills/${SkillName}/scripts/`.

# Rule 8: Taste and style

The repo should not contain grammatical errors.

The Markdown texts should be easy to read. The scripts should not be excessive, they should be understandable, they should follow simple input/output formats, they should not perform any surprising operations, and their error message must be short yet complete, and easy to parse by humans and/or other skills.
