# `agent`

Dima's proposal on how to use AI for cleaner code and better code reviews.

This repository ultimately describes a set of skills, compatible with Claude Code, Opencode, Cursor, etc.

There are also rules and meta-skills. The rules are how the skills should be written. Meta-skills are the skills that confirm that all the skills are compliant with rules.

If the user has their coding agent configured to run a skill from the command line, the skills should be compatible with this. But oftentimes this operational mode is either not configured, or is more expensive to run. In this case, the skills are very much designed so that the user can start a new agentic shell and instruct it to "Run skill ...", perhaps with parameters.
