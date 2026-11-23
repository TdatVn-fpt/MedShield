# scripts/evaluate-upstream.ps1 - Evaluate three isolated engines on the locked English corpus.
[CmdletBinding()]
param(
    [string]$UpstreamRoot = '',
    [string]$OutputPath = 'artifacts/evaluation-en.json'
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$repoRoot = Split-Path $PSScriptRoot -Parent
if (-not $UpstreamRoot) {
    $UpstreamRoot = Join-Path (Split-Path $repoRoot -Parent) 'MedShield-upstream'
}

Push-Location -LiteralPath $repoRoot
try {
    uv run --no-project --python 3.11.7 -- python -B -m ml.upstream.evaluate `
        --upstream-root $UpstreamRoot --output $OutputPath
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $exitCode
