---
name: release-workflow
description: Cut a release from develop to main. Use ONLY when the user explicitly asks to release / open the PR to main ("release time", "ouvre la PR vers main"). Bumps the SemVer version per CLAUDE.md's Releases convention, opens a plain (no-squash) develop -> main PR per the Branch Model, waits for CI, merges, closes each shipped issue with a French permalink comment, and verifies the tag/GitHub Release that CI cuts automatically on merge. Never start this unprompted.
---

# Release: develop → main

Triggered **explicitly** by the user ("ouvre la PR vers main", "release time", etc.).
**Never start this on your own.**

See `CLAUDE.md`'s **Branch Model** section for the branch table/merge rules and its
**Releases** section for the versioning convention. `develop`'s own history is already
one squash-commit per issue (each issue branch squash-merges into `develop` — see
`issue-workflow`), so a plain, non-squash PR from `develop` to `main` carries that
per-issue history over as-is. No cherry-picking, no rebase.

The generic `/release` skill doesn't fully fit here: famille-busson is a
continuously-deployed web app with no published package/artifact, so there's no
build-and-publish step — only a version bump + tag + GitHub Release for tracking what
shipped. Tag/Release creation itself is automated by `.github/workflows/release.yml` on
push to `main` (see `CLAUDE.md`'s Releases section) — this skill's job is the version
*decision* and the PR, not the tagging mechanics.

## Steps

### 1. Determine and commit the version bump (on `develop`, before opening the PR)
1. Read the current `version` from `pyproject.toml`.
2. Inspect the commits shipping in this release (`git log origin/main..develop --oneline`)
   and classify by their `<type>:` prefix:
   - Any `feat:` commit → **minor** bump (`X.Y.Z` → `X.(Y+1).0`).
   - No `feat:` but any `fix:` commit → **patch** bump (`X.Y.Z` → `X.Y.(Z+1)`).
   - Only `chore:`/`docs:`/`refactor:`/`test:` commits → **ask the user** whether this is
     worth a release at all (no user-facing change) before bumping; default to patch if
     they say yes.
3. Edit `pyproject.toml`'s `version` field to the new value.
4. **Archive shipped roadmap items.** In `ROADMAP.md`, find every item that is done
   (struck-through / marked ✅) — these are the ones shipping in this release. Move each
   one into `docs/ROADMAP_ARCHIVE.md` under a new `## vX.Y.Z` heading (English prose,
   same level of detail as the original entry), and delete it from `ROADMAP.md`.
   `ROADMAP.md` should only ever contain pending work once this step is done — if
   everything in it is done, it's fine for the file to end up with no sections left
   below the header note. Skip this step if `ROADMAP.md` has nothing marked done.
5. Commit directly on `develop` and push:
   ```
   git commit -am "chore: bump version to X.Y.Z"
   git push origin develop
   ```
   (the roadmap archive move can ride in the same commit — it's routine housekeeping,
   not worth a separate one).

### 2. Open, wait, merge
6. Confirm CI on `develop` is green (`gh run list --branch develop --limit 1`).
7. Open the PR:
   ```
   gh pr create --base main --head develop --title "release: <short summary of what's shipping>" --body "<table of shipped issues, #N + one-line title>"
   ```
8. Wait for CI to go green (poll with `gh pr checks <N> --watch --interval 15`, no manual
   prompts to the user). The repo does not allow auto-merge, so polling is required.
   **If a check fails, investigate the root cause — do not just retry.** Fix on `develop`,
   push, and re-arm the wait (never force-push, never skip hooks).
9. **Merge without squashing** — this is what preserves `develop`'s per-issue commits
   individually on `main`: `gh pr merge <N> --merge`.

### 3. Issue closing + verification
10. Fetch and capture each shipped issue's commit SHA on `main`:
    ```
    git fetch origin && git log origin/main --oneline -<N>
    ```
    Match each SHA back to its issue by the `(#<N>)` suffix in the subject line.
11. Close each shipped issue with a **French** comment linking its specific `main` SHA.
    Post the body via `--body-file`, then close (`gh issue close` has no `--body-file`):
    ```
    gh issue comment <issue-number> --body-file <path-to-comment-file>
    gh issue close <issue-number> --reason completed
    ```
    Comment body template:
    ```
    Livré sur `main` en [<sha>](https://github.com/reboulip/famille-busson/commit/<sha>) — `<commit-message>`.

    *Message généré par Claude.*
    ```
12. **Verify the automated tag/release.** The merge to `main` triggers
    `.github/workflows/release.yml`, which tags `v<version>` and creates the GitHub
    Release. Watch it to completion (`gh run list --workflow=release.yml --limit 1`) and
    confirm: `gh release view v<version>`. If it didn't fire or failed, don't hand-create
    the tag/release yourself — investigate the workflow run first (see `CLAUDE.md`'s
    Releases section for what it does).
13. Local cleanup: `git checkout main && git pull origin main`, then `git checkout develop`
    (return to the branch the session started on).

**End result:** `main` gains exactly `develop`'s new per-issue commits plus the version
bump, unchanged; a `v<version>` tag and GitHub Release exist; each closed issue carries a
permalink to its commit on `main`.

## Hotfix variant
For an urgent fix that can't wait for the normal issue → `develop` → `main` cycle (per
`CLAUDE.md`'s Branch Model): branch `hotfix/<name>` from `main`, fix, bump the **patch**
version in `pyproject.toml` as part of the same branch (so the merge to `main` still
carries a version bump for the release workflow to tag), PR back to `main` (no squash),
merge, then immediately merge `main` back into `develop` so the fix and the version bump
aren't lost on the next release (`git checkout develop && git pull && git merge main &&
git push`).
