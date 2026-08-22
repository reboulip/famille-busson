#!/usr/bin/env bash
# SessionStart hook: if a dev-pipeline sprint is in progress (a sprint-brief.md
# exists under .claude/tmp/dev-pipeline/), inject a resume instruction so a
# fresh session picks the sprint back up without the user having to re-ask.
shopt -s nullglob
briefs=(.claude/tmp/dev-pipeline/*/sprint-brief.md)
if [ ${#briefs[@]} -eq 0 ]; then
  exit 0
fi
f="${briefs[0]}"
branch="$(git branch --show-current 2>/dev/null)"
ctx="A dev-pipeline sprint is already in progress on branch '${branch}', tracked in ${f}. Resume it automatically per the dev-pipeline skill's resume protocol: re-read ROADMAP.md for remaining unchecked items, read ${f} for the wave plan / Docs pending / resolved decisions, then run 'git log --oneline <integration-branch>..HEAD' plus 'git status'/'git diff' to establish which wave is actually committed vs still sitting on the working tree (a session can end mid-wave, not at a wave boundary). Continue implementation from there without waiting for the user to re-invoke /dev-pipeline."
jq -n --arg ctx "$ctx" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
