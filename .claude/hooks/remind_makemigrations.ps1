# PostToolUse hook: remind to run makemigrations after editing a models.py file.
# Reads the tool-call JSON from stdin; stays silent for any non-models.py file.
$ErrorActionPreference = 'Stop'
try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }
    $payload = $raw | ConvertFrom-Json
    $path = $payload.tool_input.file_path
    if (-not $path) { exit 0 }
    if ($path -notmatch '[\\/]models\.py$') { exit 0 }

    $msg = "You edited a models.py file. Run 'uv run python manage.py makemigrations' then 'migrate', and weigh the impact on the Custom User Model (annuaire.Account / Person). Migrations are gitignored -- never commit them."
    $out = @{
        hookSpecificOutput = @{
            hookEventName     = 'PostToolUse'
            additionalContext = $msg
        }
    } | ConvertTo-Json -Compress
    Write-Output $out
    exit 0
} catch {
    exit 0
}
