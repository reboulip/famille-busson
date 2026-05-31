---
name: issue-workflow
description: Work one or more GitHub issues from branch to develop. Use when asked to work on / implement / fix a GitHub issue (e.g. "work on issue #15", "process issues 12 15 16"). Covers gh issue view, clarifying ambiguity, branch naming, implementing, scoped tests, squash-merging into develop locally (no PR), a French resolution comment, and parallel multi-issue orchestration via the issue-analyst / issue-implementer subagents. Never push directly to main.
---

# Issue → develop workflow

## Branch model
| Branch | Role | Direct push? |
|--------|------|-------------|
| `main` | Stable releases | Never — PR only, one commit per issue |
| `develop` | Integration branch | Yes (via squash-merge of issue branches, no PR) |
| `<type>/issue-<N>/<summary>` | One issue = one branch | Yes (your own branch) |

## Process one issue (the canonical sub-procedure)
1. Fetch the issue details: `gh issue view <number>`.
2. **If the issue is ambiguous, contradictory, or missing acceptance criteria, ask the
   user clarifying questions before writing any code.** Cover scope ("does this also cover
   X?"), non-obvious UX choices, and unmentioned edge cases. Asking up-front is far cheaper
   than shipping the wrong thing and reverting. Skip only when the issue is genuinely
   self-explanatory.
3. Infer the branch `<type>` from the issue (see types below).
4. Create the branch from up-to-date `develop` (hotfixes from `main`):
   ```
   git checkout develop && git pull origin develop
   git checkout -b <type>/issue-<number>/<short-summary>
   ```
5. Implement, run the relevant tests (see the `running-tests` skill for scope rules),
   commit on the branch.
6. If tests fail, fix on the branch and re-run. **Never merge a red branch into `develop`.**
7. If tests are green, **squash-merge directly into `develop`** locally — no PR:
   ```
   git checkout develop && git pull origin develop
   git merge --squash <type>/issue-<number>/<short-summary>
   git commit -m "<type>: <summary> (#<issue-number>)"
   git push origin develop
   git branch -D <type>/issue-<number>/<short-summary>             # local cleanup
   git push origin --delete <type>/issue-<number>/<short-summary>  # remote cleanup (if pushed)
   ```
8. **Immediately after the merge**, post a **French resolution comment** on the issue.
   Merging is your assertion that the issue is fixed, so this comment is the proof-of-work
   the user reads before testing on `develop`. Capture the squash SHA, write the body to a
   file, and post via `--body-file` (never an inline here-string — embedded `"` shred the
   body into positional args):
   ```
   git rev-parse --short HEAD    # the develop squash commit <sha>
   gh issue comment <issue-number> --body-file <path-to-comment-file>
   ```
   Body template:
   ```
   **Résolu sur `develop`** (commit <sha>).

   <2–4 short bullets: what changed, in which file/area>

   <1 sentence on WHY this resolves the issue — link the change back to the problem>

   *Message généré par Claude.*
   ```
   Do **not** close the issue here — closing happens in the `release-workflow` once the
   commit ships to `main`.

The user reviews `develop` and triggers the release-to-main flow explicitly (see the
`release-workflow` skill). Never push directly to `main`.

## Batch / parallel orchestration
For several issues at once, parallelize the **analysis** (read-only, safe to fan out) and
keep **implementation serial** (one merge into `develop` at a time → no races).

1. **Resolve the batch** — either an explicit list the user gives (`process #12 #15 #16`)
   or a query: `gh issue list --label <label> --state open` (or `--milestone <m>`).
2. **Fan out analysis (fast triage pass).** For each issue, dispatch the **`issue-analyst`**
   subagent (it runs in the background) to read the issue + code and return a structured
   plan. Move straight to the next issue without waiting; don't create branches yet
   (analysts don't need them). You'll be notified as each analyst finishes.
3. **Integration loop (serial).** As each plan lands, queue it and process the queue **one
   issue at a time**:
   a. If the analyst flagged blocking ambiguities, run step 2 of the sub-procedure (ask the
      user) before implementing.
   b. Create the issue branch from up-to-date `develop` (sub-procedure step 4).
   c. Delegate to the **`issue-implementer`** subagent (foreground) with the plan; it edits
      code + writes tests on that branch.
   d. Run the scoped tests (delegate to the **`test-runner`** subagent).
   e. On green → sub-procedure steps 7–8 (squash-merge, French comment, cleanup). On red →
      fix on the branch, never merge red.
4. **Why implementation stays serial:** `develop` merges never race and there's nothing to
   rebase; the wall-clock win comes entirely from overlapping the analyses.

> Future upgrade (parallel implementation): give `issue-implementer` `isolation: worktree`,
> but note worktrees branch from the **default branch (main)** — set `worktree.baseRef` or
> rebase each onto `develop` — each worktree needs `makemigrations`/`migrate`, and merges
> into `develop` must still be serialized.

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
- Commit message format: `<type>: <summary> (#<issue-number>)`.
- develop → main is a separate, explicit step — see the `release-workflow` skill.
