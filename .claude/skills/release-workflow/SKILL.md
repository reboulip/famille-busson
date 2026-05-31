---
name: release-workflow
description: Cut a release from develop to main via PR. Use ONLY when the user explicitly asks to release / open the PR to main ("release time", "ouvre la PR vers main"). Covers the release PR, polling CI to green, squash-merge, and closing shipped issues with commit links. Never start this unprompted.
---

# Release: develop → main

Triggered **explicitly** by the user ("ouvre la PR vers main", "release time", etc.).
**Never start this on your own.**

## Steps
1. `gh pr create --base main --head develop --title "release: <short summary>" --body "<bulleted list of issues this release closes>"`
2. Wait for CI to go green on the PR (poll with `gh pr checks <N>`, no manual prompts to
   the user).
3. Rebase-merge: `gh pr merge <N> --rebase` — replays each develop commit onto `main`
   individually, so `main` keeps **one commit per issue** with linear history (a `--squash`
   here would collapse the whole release into a single commit). Use `--admin` if branch
   protection requires it and the user is an admin.
4. For each issue referenced in the release, find its own commit on `main` and close it
   with a comment that links to that commit:
   ```
   git fetch origin main
   git log origin/main --grep "#<issue-number>" -1 --format=%h   # the issue's rebased SHA
   gh issue comment <issue-number> --body-file <path-to-comment-file>   # comment via file
   gh issue close <issue-number> --reason completed                    # then close
   ```
   Comment body, e.g.: ``Released to `main` in <sha> — <one-line description>.``
   > `gh issue close` only takes `--comment <string>` (no `--body-file`), so post the body
   > with `gh issue comment --body-file` first, then close — never an inline PowerShell
   > here-string, whose embedded `"` shred the body into positional args.
5. End result: `main` has exactly one commit per shipped issue (rebased from develop), and
   each closed issue references its own commit.

## Merge strategy
- develop → main: **rebase-merge** via PR — each develop commit (one per issue) is replayed
  onto `main` individually, preserving one commit per shipped issue with linear history.
  Not squash (single release commit) and not a plain merge (adds a merge bubble).
- Commit message format: `<type>(<scope>): <summary> (#<issue-number>)`
