# scripts/run-meddies-annotator.ps1 - Run the verified Qwen model on private blind packets.
[CmdletBinding()]
param(
    [ValidateSet('test', 'validation')]
    [string]$Split,
    [switch]$Smoke
)

$ErrorActionPreference = 'Stop'

function Get-MeddiesListener {
    # Return the local listener or no results if the port is free. Surface other query failures.
    param([int]$Port)

    try {
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    } catch {
        if ($_.FullyQualifiedErrorId -ne 'CmdletizationQuery_NotFound,Get-NetTCPConnection') { throw }
    }
}

function Assert-MeddiesListener {
    # Require the loopback listener to be owned by the pinned server started for this run.
    param([int]$Port, [int]$ProcessId)

    $listeners = @(Get-MeddiesListener -Port $Port)
    if ($listeners.Count -ne 1 -or
        $listeners[0].LocalAddress -ne '127.0.0.1' -or
        $listeners[0].OwningProcess -ne $ProcessId) {
        throw 'The Meddies loopback listener is not owned exclusively by the local runtime for this run.'
    }
}

$port = 18240
$mutex = [Threading.Mutex]::new($false, "Global\MedShield.Meddies.Annotator.$port")
$mutexAcquired = $false
$process = $null
$enteredRepo = $false
try {
    try {
        $mutexAcquired = $mutex.WaitOne(0)
    } catch [Threading.AbandonedMutexException] {
        $mutexAcquired = $true
    }
    if (-not $mutexAcquired) {
        throw 'Another Meddies annotation process already holds the local port lock.'
    }
    if (@(Get-MeddiesListener -Port $port).Count -ne 0) {
        throw 'The Meddies local port is already occupied.'
    }

    $repo = Split-Path $PSScriptRoot -Parent
    $meddies = Join-Path $repo 'artifacts/local/meddies'
    $runtime = Join-Path $meddies 'llm-qwen'
    $model = 'Qwen2.5-7B-Instruct-Q4_K_M'
    $hashes = @(
        'dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db',
        '539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a'
    )
    $parts = @(1, 2 | ForEach-Object {
        Join-Path $runtime ('qwen2.5-7b-instruct-q4_k_m-{0:00000}-of-00002.gguf' -f $_)
    })
    for ($i = 0; $i -lt $parts.Count; $i++) {
        if ((Get-FileHash -LiteralPath $parts[$i]).Hash -ine $hashes[$i]) {
            throw 'Shard Qwen does not match the registered SHA-256.'
        }
    }
    $server = Join-Path $runtime 'llama-server.exe'
    $runtimeExitMode = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $version = (& $server --version 2>&1 | ForEach-Object { "$_" }) -join [Environment]::NewLine
    } finally {
        $ErrorActionPreference = $runtimeExitMode
    }
    if ($version -notmatch 'build 12754, commit 244640b7f') {
        throw 'llama.cpp runtime differs from the registered release.'
    }
    $argsForServer = @(
        '-m', ('"{0}"' -f $parts[0]), '--alias', $model,
        '--host', '127.0.0.1', '--port', $port,
        '--ctx-size', '8192', '--parallel', '1', '--threads', '6',
        '--n-gpu-layers', '0', '--no-webui', '--log-disable'
    )
    $process = Start-Process -FilePath $server -ArgumentList $argsForServer -WorkingDirectory $runtime -WindowStyle Hidden -PassThru
    Push-Location $repo
    $enteredRepo = $true
    $healthy = $false
    for ($i = 0; $i -lt 90; $i++) {
        if ($process.HasExited) { throw 'The local runtime exited before becoming healthy.' }
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$port/health" -TimeoutSec 2
            if ($health.status -eq 'ok') { $healthy = $true; break }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $healthy) { throw 'The local runtime did not report ready.' }
    Assert-MeddiesListener -Port $port -ProcessId $process.Id
    $guide = Join-Path $repo 'docs/annotation-guide.md'
    if ($Smoke) {
        $packet = Join-Path $runtime 'synthetic-smoke.jsonl'
        $out = Join-Path $runtime 'synthetic-smoke-output'
        if (Test-Path -LiteralPath (Join-Path $out 'annotations-b.jsonl')) {
            throw 'A completed smoke receipt already exists.'
        }
        if (-not (Test-Path -LiteralPath $packet)) {
            $note = @{note_id = 'smoke-demo'; text = 'Nguoi benh Mai An, sinh ngay 03/02/1995.'}
            $line = ($note | ConvertTo-Json -Compress) + [char]10
            [IO.File]::WriteAllText($packet, $line, [Text.UTF8Encoding]::new($false))
        }
        uv run --locked python -X utf8 -m ml.meddies_annotator $packet $guide $out --port $port
        if ($LASTEXITCODE -ne 0) { throw 'Local LLM smoke did not finish.' }
    } else {
        $failed = @()
        $splits = @('validation', 'test')
        if ($Split) { $splits = @($Split) }
        foreach ($name in $splits) {
            $packet = Join-Path $meddies "step3-source-isolated/$name-blind.jsonl"
            $out = Join-Path $meddies "step4/$name-qwen"
            if ((Test-Path -LiteralPath (Join-Path $out 'annotations-b.jsonl')) -and
                (Test-Path -LiteralPath (Join-Path $out 'completion-manifest.json'))) { continue }
            Assert-MeddiesListener -Port $port -ProcessId $process.Id
            uv run --locked python -X utf8 -m ml.meddies_annotator $packet $guide $out --port $port
            if ($LASTEXITCODE -ne 0) { $failed += $name }
        }
        if ($failed.Count -gt 0) { throw "Annotation incomplete for: $($failed -join ', ')." }
    }
} finally {
    try {
        if ($process -and -not $process.HasExited) { Stop-Process -InputObject $process }
    } finally {
        if ($mutexAcquired) { $mutex.ReleaseMutex() }
        $mutex.Dispose()
        if ($enteredRepo) { Pop-Location }
    }
}
