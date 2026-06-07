#!/bin/sh
# Print a fresh SkillRunId in the default format codified in .theloop/SKILLS-META-RULES.md:
# YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}, e.g. 20260607-153012-kqzwxy.
set -eu
printf '%s-%s\n' "$(date +%Y%m%d-%H%M%S)" "$(LC_ALL=C tr -dc 'a-z' </dev/urandom | head -c 6)"
