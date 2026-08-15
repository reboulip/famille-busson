# Stop hook: reinforce the end-of-task A/B/C ritual.
# Fires ONLY when (a) the worktree is dirty AND (b) we are not on an issue branch
# (the issue-workflow has its own commit/squash-merge flow, so the generic ritual
# does not apply there). Guards against the Stop-hook loop via stop_hook_active.
$ErrorActionPreference = 'Stop'
try {
    $raw = [Console]::In.ReadToEnd()
    if ($raw) {
        $payload = $raw | ConvertFrom-Json
        if ($payload.stop_hook_active -eq $true) { exit 0 }  # already continuing — avoid loop
    }

    $status = git status --porcelain
    if (-not $status) { exit 0 }                              # clean worktree — silent

    $branch = git rev-parse --abbrev-ref HEAD
    if ($branch -match '/issue-.+/') { exit 0 }               # inside issue workflow — silent

    $reason = "Uncommitted changes on branch '$branch'. Run the end-of-task ritual before stopping. " +
        "If tests were NOT run during this task, offer: A) run relevant tests and commit if green, " +
        "B) run relevant tests and report (no commit), C) commit without running tests -- and state which " +
        "test files apply (see /test-select's scope rules). If tests already ran green, offer only " +
        "A) commit, B) don't commit yet. Tests gate commits: never commit after a failed run."
    $out = @{ decision = 'block'; reason = $reason } | ConvertTo-Json -Compress
    Write-Output $out
    exit 0
} catch {
    exit 0
}
