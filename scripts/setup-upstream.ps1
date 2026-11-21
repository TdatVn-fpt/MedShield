# scripts/setup-upstream.ps1 - Set up isolated Windows benchmark environments and smoke engines.
[CmdletBinding()]
param(
    [ValidateSet('all', 'presidio', 'philter', 'pydeid')]
    [string]$Engine = 'all',
    [switch]$SmokeOnly,
    [string]$UpstreamRoot = ''
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$repoRoot = Split-Path $PSScriptRoot -Parent
$environmentRoot = Join-Path $repoRoot '.venv-upstream-g2'
$philterUrl = 'https://github.com/BCHSI/philter-ucsf.git'
$philterRevision = '4da3cf31c9bfbfd66c66b141c45ba7a47628dd0a'
$versions = @{ presidio = '3.11.7'; philter = '3.10.20'; pydeid = '3.11.7' }

if ($UpstreamRoot) {
    $UpstreamRoot = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(
        $UpstreamRoot
    )
} else {
    $UpstreamRoot = Join-Path (Split-Path $repoRoot -Parent) 'MedShield-upstream'
}

function Invoke-Checked {
    <# .SYNOPSIS Runs a native program and throws when the exit code is nonzero. #>
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Native command $([IO.Path]::GetFileName($Program)) exited with code $LASTEXITCODE."
    }
}

function Confirm-PhilterCheckout {
    <# .SYNOPSIS Prepares the pinned Philter checkout if absent and validates its provenance. #>
    param([string]$Checkout)
    if (-not ($SmokeOnly -or (Test-Path -LiteralPath $Checkout))) {
        New-Item -ItemType Directory -Force -Path $UpstreamRoot | Out-Null
        Invoke-Checked git @('init', '--quiet', $Checkout)
        Invoke-Checked git @('-C', $Checkout, 'remote', 'add', 'origin', $philterUrl)
    }

    $origin = Invoke-Checked git @('-C', $Checkout, 'remote', 'get-url', 'origin')
    if ($origin -cne $philterUrl) {
        throw 'Philter origin differs from the pinned repository.'
    }
    $revision = & git -C $Checkout rev-parse --verify --quiet HEAD
    if ($LASTEXITCODE -ne 0 -and -not $SmokeOnly) {
        Invoke-Checked git @('-C', $Checkout, 'fetch', '--depth=1', 'origin', $philterRevision)
        Invoke-Checked git @('-C', $Checkout, 'checkout', '--detach', 'FETCH_HEAD')
        $revision = Invoke-Checked git @('-C', $Checkout, 'rev-parse', 'HEAD')
    }
    if ($revision -cne $philterRevision) {
        throw "Philter checkout must be at the pinned revision $philterRevision."
    }
    $trackedChanges = Invoke-Checked git @(
        '-C', $Checkout, 'status', '--porcelain', '--untracked-files=no'
    )
    if ($trackedChanges) {
        throw 'Philter checkout has tracked changes.'
    }
}

function Invoke-EngineSmoke {
    <# .SYNOPSIS Sets up one engine and emits its JSON array of covered positions. #>
    param([string]$Name)
    $environment = Join-Path $environmentRoot $Name
    $python = Join-Path $environment 'Scripts/python.exe'
    $version = $versions[$Name]
    $arguments = @('-B', '-m', 'ml.upstream.smoke', $Name)

    if (-not $SmokeOnly -and -not (Test-Path -LiteralPath $python -PathType Leaf)) {
        Invoke-Checked uv @('venv', '--no-project', '--python', $version, $environment) |
            Out-Host
    }
    $actualVersion = Invoke-Checked $python @(
        '-B', '-c', 'import platform; print(platform.python_version())'
    )
    if ($actualVersion -cne $version) {
        throw "$Name requires Python $version. Found $actualVersion."
    }
    if (-not $SmokeOnly) {
        $lock = Join-Path $repoRoot "ml/upstream/$Name.lock.txt"
        Invoke-Checked uv @('pip', 'sync', '--python', $python, '--link-mode', 'copy', $lock) |
            Out-Host
        Invoke-Checked uv @('pip', 'check', '--python', $python) | Out-Host
    }

    if ($Name -eq 'philter') {
        $checkout = Join-Path $UpstreamRoot 'philter'
        $nltkData = Join-Path $environment 'nltk_data'
        Confirm-PhilterCheckout $checkout
        if (-not $SmokeOnly) {
            Invoke-Checked $python @('-B', '-m', 'ml.upstream.resources', $nltkData) | Out-Host
        }
        $arguments += @('--philter-root', $checkout, '--nltk-data', $nltkData)
    }

    Invoke-Checked $python $arguments
}

$engines = @($Engine)
if ($Engine -eq 'all') {
    $engines = @('presidio', 'philter', 'pydeid')
}
$failures = 0
Push-Location -LiteralPath $repoRoot
try {
    foreach ($name in $engines) {
        try {
            Invoke-EngineSmoke $name
        } catch {
            [Console]::Error.WriteLine("$($name): $($_.Exception.Message)")
            $failures++
        }
    }
} finally {
    Pop-Location
}
if ($failures -gt 0) {
    exit 1
}
