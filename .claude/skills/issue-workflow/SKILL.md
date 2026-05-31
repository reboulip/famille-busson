---
name: issue-workflow
description: Work a GitHub issue from branch to develop. Use when asked to work on / implement / fix a GitHub issue (e.g. "work on issue #15"). Covers gh issue view, inferring branch type, branch naming, implementing, running scoped tests, and squash-merging into develop locally (no PR). Never push directly to main.
---

# Issue → develop workflow

## Branch model
| Branch | Role | Direct push? |
|--------|------|-------------|
| `main` | Stable releases | Never — PR only, one commit per issue |
| `develop` | Integration branch | Yes (via squash-merge of issue branches, no PR) |
| `<type>/issue-<N>/<summary>` | One issue = one branch | Yes (your own branch) |

## Steps
1. Fetch the issue details: `gh issue view <number>`
2. Infer the branch `<type>` from the issue description (see types below).
3. Create the branch from up-to-date `develop` (hotfixes from `main`):
   ```
   git checkout develop && git pull origin develop
   git checkout -b <type>/issue-<number>/<short-summary>
   ```
4. Implement, run the relevant tests (see the `running-tests` skill for scope rules),
   commit on the branch.
5. If tests are green, **squash-merge directly into `develop`** locally — no PR:
   ```
   git checkout develop && git pull origin develop
   git merge --squash <type>/issue-<number>/<short-summary>
   git commit -m "<type>: <summary> (#<issue-number>)"
   git push origin develop
   git branch -D <type>/issue-<number>/<short-summary>      # local cleanup
   git push origin --delete <type>/issue-<number>/<short-summary>   # remote cleanup (if pushed)
   ```
6. If tests fail, fix on the branch and re-run. Never merge a red branch into `develop`.
7. **Comment on the issue** that it's fixed in `develop` (leave it open — the
   `release-workflow` closes it when the release lands on `main`). Capture the squash
   commit's SHA, then post via `--body-file` (never an inline here-string — embedded `"`
   shred the body into positional args):
   ```
   git rev-parse --short HEAD    # the develop squash commit
   gh issue comment <issue-number> --body-file <path-to-comment-file>
   ```
   Body, e.g.: ``Fixed in `develop` via <sha>. Will close on the next release to `main`.``
8. Working in parallel on multiple issues is fine — rebase each issue branch onto
   `develop` as often as needed to stay current:
   ```
   git checkout <type>/issue-<N>/<summary>
   git fetch origin && git rebase origin/develop
   ```

The user reviews `develop` and triggers the release-to-main PR explicitly (see the
`release-workflow` skill). Never push directly to `main`.

## Branch naming convention
`<type>/issue-<number>/<short-summary>` e.g. `feat/issue-12/person-avatar-upload`

| Type | When to use |
|------|-------------|
| `feat` | New feature or user-visible capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring, no behaviour change |
| `chore` | Dependency update, tooling, CI, config |
| `docs` | Documentation only |
| `test` | Tests only |

## Merge strategy
- Issue → develop: local squash-merge (no PR) — one issue = one commit on `develop`.
- Commit message format: `<type>(<scope>): <summary> (#<issue-number>)`
