---
name: release-workflow
description: Cut a release from develop to main. Use ONLY when the user explicitly asks to release / open the PR to main ("release time", "ouvre la PR vers main"). Cherry-picks the new issue commits onto a release branch off main, opens a PR, rebase-merges it (one commit per issue), and closes each shipped issue with a French permalink comment. Never start this unprompted.
---

# Release: develop → main

Triggered **explicitly** by the user ("ouvre la PR vers main", "release time", etc.).
**Never start this on your own.**

**Goal: each shipped issue is exactly one commit on `main`** (`feat:` / `fix:` / … with the
issue number in the subject), so `git log main` is a clean release history aligned 1-to-1
with closed issues.

**Why not a direct `develop → main` PR?** `main` was built from squash-merges, so develop's
history holds many commits whose content already shipped to `main` as squashes. A direct
`develop → main` rebase-and-merge replays those already-shipped commits (conflicts /
duplicates), and a squash collapses every issue into one indistinguishable blob.
Cherry-picking the relevant commits onto a release branch sidesteps both.

## Steps
1. Identify the develop commits to ship (typically the new issue commits since the last
   release, plus any chore/docs commits the user explicitly approved for `main`).
2. Create a release branch from up-to-date `main`:
   ```
   git checkout main && git pull origin main
   git checkout -b release/<short-summary>          # e.g. release/issues-3-4-5-6
   ```
3. Cherry-pick the chosen develop commits in chronological order (oldest first). After each
   `git cherry-pick <sha>`, immediately `git commit --amend -m "<type>: <summary> (#<n>)"`
   to drop any trailing PR-number suffix GitHub added on squash-merge.
4. Push the release branch: `git push -u origin release/<short-summary>`.
5. Open the PR to `main`:
   ```
   gh pr create --base main --head release/<short-summary> --title "release: <short summary>" --body "<table of shipped issues>"
   ```
6. Wait for CI to go green (poll with `gh pr checks <N> --watch --interval 15`, no manual
   prompts to the user). The repo does not allow auto-merge, so polling is required.
7. **Rebase-merge** (NOT squash): `gh pr merge <N> --rebase`. This replays each cherry-picked
   commit onto `main` individually, preserving the one-commit-per-issue mapping. The repo
   allows rebase merges.
8. Fetch and capture each issue's commit SHA on `main`:
   ```
   git fetch origin && git log origin/main --oneline -<N>
   ```
9. Close each shipped issue with a **French** comment linking its specific `main` SHA. Post
   the body via `--body-file`, then close (`gh issue close` has no `--body-file`):
   ```
   gh issue comment <issue-number> --body-file <path-to-comment-file>
   gh issue close <issue-number> --reason completed
   ```
   Comment body template:
   ```
   Livré sur `main` en [<sha>](https://github.com/reboulip/famille-busson/commit/<sha>) — `<commit-message>`.

   *Message généré par Claude.*
   ```
10. Local cleanup: `git checkout main && git pull origin main`, then delete the local
    release branch (GitHub auto-deletes the remote branch on merge).

**End result:** `main` gains exactly one commit per shipped issue; each closed issue carries
a permalink to its commit; the release branch is ephemeral and gone after merge.

## Merge strategy
- develop → main: cherry-pick the new issue commits onto a `release/<summary>` branch off
  `main`, open a PR, **rebase-merge** so each commit lands individually. Never squash this PR
  (collapses issues into one commit) and never rebase-merge straight from `develop` (replays
  pre-release commits already squashed on `main`).
- Commit message format: `<type>: <summary> (#<issue-number>)`.
