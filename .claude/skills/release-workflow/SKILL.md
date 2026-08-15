---
name: release-workflow
description: Cut a release from develop to main. Use ONLY when the user explicitly asks to release / open the PR to main ("release time", "ouvre la PR vers main"). Opens a plain (no-squash) develop -> main PR per CLAUDE.md's Branch Model, waits for CI, merges, and closes each shipped issue with a French permalink comment. Never start this unprompted.
---

# Release: develop → main

Triggered **explicitly** by the user ("ouvre la PR vers main", "release time", etc.).
**Never start this on your own.**

See `CLAUDE.md`'s **Branch Model** section for the full branch table and merge rules.
`develop`'s own history is already one squash-commit per issue (each issue branch
squash-merges into `develop` — see `issue-workflow`), so a plain, non-squash PR from
`develop` to `main` carries that per-issue history over as-is. No cherry-picking, no
rebase — `main` gains exactly `develop`'s new commits, unmodified.

The generic `/release` skill doesn't apply here: famille-busson has no version number,
tag, or published artifact to bump/cut — it's a continuously-deployed web app, not a
package release.

## Steps
1. Confirm `develop` is pushed and CI on it is green (`gh run list --branch develop --limit 1`).
2. Open the PR:
   ```
   gh pr create --base main --head develop --title "release: <short summary of what's shipping>" --body "<table of shipped issues, #N + one-line title>"
   ```
3. Wait for CI to go green (poll with `gh pr checks <N> --watch --interval 15`, no manual
   prompts to the user). The repo does not allow auto-merge, so polling is required.
   **If a check fails, investigate the root cause — do not just retry.** Fix on `develop`,
   push, and re-arm the wait (never force-push, never skip hooks).
4. **Merge without squashing** — this is what preserves `develop`'s per-issue commits
   individually on `main`: `gh pr merge <N> --merge`.
5. Fetch and capture each shipped issue's commit SHA on `main`:
   ```
   git fetch origin && git log origin/main --oneline -<N>
   ```
   Match each SHA back to its issue by the `(#<N>)` suffix in the subject line.
6. Close each shipped issue with a **French** comment linking its specific `main` SHA. Post
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
7. Local cleanup: `git checkout main && git pull origin main`, then `git checkout develop`
   (return to the branch the session started on).

**End result:** `main` gains exactly `develop`'s new per-issue commits, unchanged; each
closed issue carries a permalink to its commit on `main`.

## Hotfix variant
For an urgent fix that can't wait for the normal issue → `develop` → `main` cycle (per
`CLAUDE.md`'s Branch Model): branch `hotfix/<name>` from `main`, fix, PR back to `main`
(no squash), merge, then immediately merge `main` back into `develop` so the fix isn't
lost on the next release (`git checkout develop && git pull && git merge main && git push`).
