#requires -version 5.1
<#
PaperForge local pre-certification kit (Real-Machine Verification Standard §7;
the WACK analog: run it on any machine before claiming anything).

Steps:
  1. host-probe  -> host-profile.json (declared profile + precondition checks)
  2. runtime smoke: resolve the published pointer (fallback: PATH python) and run
     `python -m paperforge --vault <temp> probe all --json` with a bounded
     timeout; record duration + exit code (a timeout is recorded as such, not
     hidden)
  3. emit conformance.json (steps + raw results) for the report pipeline

Usage:
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/certify.ps1
  powershell ... -File scripts/certify.ps1 -OutDir D:\evidence -ProbeTimeoutSec 240

Run it from a directory OUTSIDE the repository: with the repo root as CWD the
probe would import the source tree instead of the installed runtime.
#>
param(
  [string]$OutDir = ".",
  [int]$ProbeTimeoutSec = 240
)

$ErrorActionPreference = "Continue"
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
$OutDir = [System.IO.Path]::GetFullPath($OutDir)

$steps = New-Object System.Collections.ArrayList
function Add-Step([string]$id, [string]$status, $detail) {
  [void]$steps.Add([pscustomobject]@{ id = $id; status = $status; detail = $detail })
}

# ── 1. host probe ───────────────────────────────────────────────────────────
$profilePath = Join-Path $OutDir 'host-profile.json'
& (Join-Path $scriptDir 'host-probe.ps1') -OutFile $profilePath | Out-Null
$hostProfile = $null
try {
  $hostProfile = Get-Content -LiteralPath $profilePath -Raw | ConvertFrom-Json
  Add-Step 'host_probe' 'pass' "profile=$($hostProfile.host_profile); preconditions_ok=$($hostProfile.preconditions_ok)"
} catch {
  Add-Step 'host_probe' 'fail' "$($_.Exception.Message)"
}

# ── 2. resolve the runtime to smoke ─────────────────────────────────────────
$pointerFile = Join-Path $env:USERPROFILE '.paperforge\runtime\pointer.json'
$pythonExe = 'python'
$pointerState = 'missing'
if (Test-Path -LiteralPath $pointerFile) {
  try {
    $ptr = Get-Content -LiteralPath $pointerFile -Raw | ConvertFrom-Json
    if ($ptr.python_path -and (Test-Path -LiteralPath $ptr.python_path)) {
      $pythonExe = [string]$ptr.python_path
      $pointerState = "published:$($ptr.paperforge_version)"
    } else { $pointerState = 'invalid' }
  } catch { $pointerState = 'unreadable' }
}
Add-Step 'runtime_pointer' (if ($pointerState -like 'published*') { 'pass' } else { 'warn' }) "$pointerState ($pythonExe)"

# version through the resolved interpreter (metadata, not --version parsing).
# Run from a neutral cwd: the repo root on sys.path would shadow the installed
# distribution's metadata with a source egg-info.
$version = $null
try {
  Push-Location $env:TEMP
  $version = (& $pythonExe -c "import importlib.metadata as m; print(m.version('paperforge'))" 2>&1 | Out-String).Trim()
  if ($LASTEXITCODE -ne 0) { $version = $null }
} catch { $version = $null } finally { Pop-Location }
if ($version) {
  Add-Step 'paperforge_version' 'pass' $version
} else {
  Add-Step 'paperforge_version' 'fail' "paperforge metadata not resolvable via $pythonExe"
}

# ── 3. bounded `probe all` smoke against a temp vault ───────────────────────
$tmpVault = Join-Path $env:TEMP ('pf-certify-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmpVault -Force | Out-Null
$stdoutFile = Join-Path $tmpVault 'probe.out.json'
$stderrFile = Join-Path $tmpVault 'probe.err.txt'
$probeResult = [pscustomobject]@{ status = 'unknown'; duration_s = $null; exit_code = $null; output_head = $null }
$sw = [System.Diagnostics.Stopwatch]::StartNew()
try {
  $proc = Start-Process -FilePath $pythonExe -ArgumentList @('-m', 'paperforge', '--vault', $tmpVault, 'probe', 'all', '--json') `
    -NoNewWindow -PassThru -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile
  $completed = $false
  try { $proc | Wait-Process -Timeout $ProbeTimeoutSec -ErrorAction Stop; $completed = $true } catch {}
  if ($completed) {
    $probeResult.status = if ($proc.ExitCode -eq 0) { 'pass' } else { 'fail' }
    $probeResult.exit_code = $proc.ExitCode
  } else {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    $probeResult.status = 'timeout'
  }
} catch {
  $probeResult.status = 'error'
  $probeResult.output_head = "$($_.Exception.Message)"
} finally {
  $sw.Stop()
  $probeResult.duration_s = [math]::Round($sw.Elapsed.TotalSeconds, 1)
}
if (Test-Path -LiteralPath $stdoutFile) {
  $head = (Get-Content -LiteralPath $stdoutFile -TotalCount 1 -ErrorAction SilentlyContinue)
  if ($head) { $probeResult.output_head = $head.Substring(0, [Math]::Min(300, $head.Length)) }
}
Add-Step 'probe_all_smoke' $probeResult.status "duration=$($probeResult.duration_s)s exit=$($probeResult.exit_code)"
try { Remove-Item -LiteralPath $tmpVault -Recurse -Force -ErrorAction SilentlyContinue } catch {}

# ── emit conformance.json ───────────────────────────────────────────────────
$failCount = @($steps | Where-Object { $_.status -eq 'fail' }).Count
$warnCount = @($steps | Where-Object { $_.status -eq 'warn' -or $_.status -eq 'timeout' }).Count
$result = [pscustomobject][ordered]@{
  schema        = 'paperforge.conformance/1'
  tool          = 'scripts/certify.ps1 v1'
  generated_at  = (Get-Date).ToUniversalTime().ToString('o')
  host_profile  = if ($hostProfile) { $hostProfile.host_profile } else { 'unknown' }
  profile_source = 'v0 (unfrozen)'
  machine       = if ($hostProfile) { $hostProfile.machine } else { $null }
  runtime       = [pscustomobject][ordered]@{ pointer = $pointerState; python = $pythonExe; version = $version }
  probe_all     = $probeResult
  steps         = @($steps)
  status        = if ($failCount -gt 0) { 'FAILED' } elseif ($warnCount -gt 0) { 'PASS_WITH_WARNINGS' } else { 'PASS' }
}
$json = $result | ConvertTo-Json -Depth 8
$confPath = Join-Path $OutDir 'conformance.json'
[System.IO.File]::WriteAllText($confPath, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
Write-Host "conformance written: $confPath"
Write-Host ("status={0} profile={1} " -f $result.status, $result.host_profile + ($steps | ForEach-Object { "[$($_.id)=$($_.status)]" } | Out-String))
$json
