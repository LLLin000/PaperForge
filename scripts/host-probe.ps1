#requires -version 5.1
<#
PaperForge host probe (Real-Machine Verification Standard §7).

Declares which host profile (P0/P1/P2) this Windows machine falls into and
probes the capability preconditions the standard requires (python discovery,
PyPI reachability, runtime root writability, free space, long paths, keyring,
VC runtime, AV products, OneDrive redirection).

Output: host-profile.json (UTF-8, no BOM) + the same JSON on stdout.
The output is the `machine`/`host_profile` source for evidence files; it is
read-mostly (only a temp probe file is written next to the deepest existing
ancestor of ~/.paperforge/runtime and removed again).

Usage:  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/host-probe.ps1
        powershell ... -File scripts/host-probe.ps1 -OutFile D:\evidence\host-profile.json
#>
param(
  [string]$OutFile = "host-profile.json"
)

$ErrorActionPreference = "Continue"
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}
$checks = New-Object System.Collections.ArrayList

function Add-Check([string]$id, [string]$status, [string]$detail) {
  [void]$checks.Add([pscustomobject]@{ id = $id; status = $status; detail = $detail })
}

function Get-RegValue([string]$path, [string]$name) {
  try { return (Get-ItemProperty -Path $path -Name $name -ErrorAction Stop).$name }
  catch { return $null }
}

# ── OS facts ────────────────────────────────────────────────────────────────
$osBuild = [string](Get-RegValue 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' 'CurrentBuildNumber')
$osCaption = [string](Get-RegValue 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' 'ProductName')
$arch = [string]$env:PROCESSOR_ARCHITECTURE
if ($env:PROCESSOR_ARCHITEW6432) { $arch = [string]$env:PROCESSOR_ARCHITEW6432 }

$userProfile = [string]$env:USERPROFILE
$userName = Split-Path -Leaf $userProfile
$usernameAscii = ($userName -match '^[\x20-\x7E]+$')
$pathHasSpace = ($userProfile -match '\s')
if (-not $usernameAscii) { Add-Check 'username_ascii' 'warn' "user name is not ASCII: $userName" }
else { Add-Check 'username_ascii' 'pass' $userName }
if ($pathHasSpace) { Add-Check 'user_path_has_space' 'warn' $userProfile }
else { Add-Check 'user_path_has_space' 'pass' $userProfile }

try {
  $documents = [Environment]::GetFolderPath('MyDocuments')
  if ($documents -match 'OneDrive') { Add-Check 'onedrive_redirected' 'warn' "Documents -> $documents" }
  else { Add-Check 'onedrive_redirected' 'pass' $documents }
} catch { Add-Check 'onedrive_redirected' 'unknown' "$($_.Exception.Message)" }

# ── Python discovery (mirrors managed-runtime.ts candidate chain) ───────────
$pythonSource = 'none'
$pythonVersion = $null
$pyVersion = $null
try {
  $pyVersion = (& py -3 --version 2>&1 | Out-String).Trim()
  if ($LASTEXITCODE -eq 0 -and $pyVersion -match 'Python (\d+\.\d+)') { $pythonSource = 'py-launcher' }
} catch {}
if ($pythonSource -eq 'none') {
  try {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
      $pythonVersion = (& python --version 2>&1 | Out-String).Trim()
      if ($LASTEXITCODE -eq 0 -and $pythonVersion -match 'Python (\d+\.\d+)') {
        if ($cmd.Source -match 'WindowsApps') { $pythonSource = 'store' }
        else { $pythonSource = 'python.org' }
      }
    }
  } catch {}
}
if ($pythonSource -eq 'none') { Add-Check 'python_discovery' 'fail' 'no working py -3 / python >= 3.11 found' }
else {
  $pyVerStr = if ($pyVersion) { $pyVersion } else { $pythonVersion }
  $pyMinor = 0.0
  if ($pyVerStr -match 'Python (\d+\.\d+)') { $pyMinor = [double]$matches[1] }
  if ($pyMinor -gt 0 -and $pyMinor -lt 3.11) {
    Add-Check 'python_discovery' 'fail' "$pythonSource $pyVerStr (< 3.11)"
  } elseif ($pyMinor -gt 3.12) {
    Add-Check 'python_discovery' 'warn' "$pythonSource $pyVerStr above declared P0 range (3.11-3.12); [vector] wheels may be missing"
  } else {
    Add-Check 'python_discovery' 'pass' "$pythonSource $pyVerStr"
  }
}

# keyring backend (only meaningful with a working interpreter)
if ($pythonSource -ne 'none') {
  try {
    $kr = (& python -c "import keyring; print(keyring.get_keyring().__class__.__module__ + '.' + keyring.get_keyring().__class__.__name__)" 2>&1 | Out-String).Trim()
    Add-Check 'keyring_backend' 'pass' $kr
  } catch { Add-Check 'keyring_backend' 'unknown' "$($_.Exception.Message)" }
} else { Add-Check 'keyring_backend' 'unknown' 'no python available to query keyring' }

# ── Network / PyPI ──────────────────────────────────────────────────────────
$proxy = @($env:HTTP_PROXY, $env:HTTPS_PROXY) | Where-Object { $_ } | Select-Object -First 1
$indexUrl = [string]$env:PIP_INDEX_URL
$pypiOk = $false
try {
  $resp = Invoke-WebRequest -Uri 'https://pypi.org/simple/' -Method Head -TimeoutSec 8 -UseBasicParsing
  $pypiOk = ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400)
} catch { $pypiOk = $false }
if ($pypiOk) { Add-Check 'pypi_reachable' 'pass' 'HEAD https://pypi.org/simple/ ok' }
elseif ($indexUrl) { Add-Check 'pypi_reachable' 'warn' "pypi.org unreachable; PIP_INDEX_URL=$indexUrl configured" }
else { Add-Check 'pypi_reachable' 'fail' 'pypi.org unreachable and no PIP_INDEX_URL configured' }
if ($proxy) { Add-Check 'proxy_env' 'warn' $proxy } else { Add-Check 'proxy_env' 'pass' 'no HTTP(S)_PROXY set' }
$networkKind = if ($proxy -or $indexUrl) { 'proxy' } elseif ($pypiOk) { 'direct' } else { 'offline' }

# ── Runtime root writability (deepest existing ancestor + temp probe file) ──
$runtimeRoot = Join-Path $userProfile '.paperforge\runtime'
$probeDone = $false
$ancestor = $runtimeRoot
while ($ancestor -and -not (Test-Path -LiteralPath $ancestor)) { $ancestor = Split-Path -Parent $ancestor }
try {
  $probeFile = Join-Path $ancestor ('.pf-probe-' + [guid]::NewGuid().ToString('N') + '.tmp')
  [System.IO.File]::WriteAllText($probeFile, 'ok')
  Remove-Item -LiteralPath $probeFile -Force
  $probeDone = $true
  Add-Check 'runtime_root_writable' 'pass' "write probe ok under $ancestor"
} catch { Add-Check 'runtime_root_writable' 'fail' "$($_.Exception.Message) (ancestor: $ancestor)" }

# ── Free space on the profile drive ─────────────────────────────────────────
$freeGb = $null
try {
  $drive = (Split-Path -Qualifier $userProfile).TrimEnd(':')
  $d = Get-PSDrive -Name $drive
  $freeGb = [math]::Round($d.Free / 1GB, 1)
  if ($freeGb -lt 2) { Add-Check 'free_space' 'fail' "$freeGb GB free on ${drive}:" }
  elseif ($freeGb -lt 5) { Add-Check 'free_space' 'warn' "$freeGb GB free on ${drive}:" }
  else { Add-Check 'free_space' 'pass' "$freeGb GB free on ${drive}:" }
} catch { Add-Check 'free_space' 'unknown' "$($_.Exception.Message)" }

# ── Long paths ──────────────────────────────────────────────────────────────
$lp = Get-RegValue 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' 'LongPathsEnabled'
if ($lp -eq 1) { Add-Check 'long_paths' 'pass' 'LongPathsEnabled=1' }
else { Add-Check 'long_paths' 'warn' "LongPathsEnabled=$lp (MAX_PATH applies)" }

# ── VC runtime ──────────────────────────────────────────────────────────────
$vc = @('vcruntime140.dll', 'msvcp140.dll') | ForEach-Object { Test-Path (Join-Path $env:SystemRoot "System32\$_") }
if ($vc -notcontains $false) { Add-Check 'vc_runtime' 'pass' 'vcruntime140 + msvcp140 present' }
else { Add-Check 'vc_runtime' 'warn' 'one of vcruntime140.dll/msvcp140.dll missing' }

# ── Antivirus (best effort) ─────────────────────────────────────────────────
$defenderRealTime = $null
try {
  $mp = Get-MpComputerStatus -ErrorAction Stop
  $defenderRealTime = [bool]$mp.RealTimeProtectionEnabled
} catch {}
$avProducts = @()
try {
  $avProducts = @(Get-CimInstance -Namespace 'root\SecurityCenter2' -Class AntiVirusProduct -ErrorAction Stop |
    Select-Object -ExpandProperty displayName)
} catch {}
$thirdParty = @($avProducts | Where-Object { $_ -and $_ -notmatch 'Windows Defender|Microsoft Defender' })
$defenderOnly = ($thirdParty.Count -eq 0)
$avStatus = if ($thirdParty.Count -gt 0) { 'warn' } else { 'pass' }
$avList = if ($avProducts.Count -gt 0) { $avProducts } else { @('unknown') }
$avDetail = "defender_realtime=$defenderRealTime; products=" + ($avList -join '; ')
Add-Check 'antivirus' $avStatus $avDetail

# ── Profile verdict (standard §4; v0, unfrozen) ─────────────────────────────
$reasons = New-Object System.Collections.ArrayList
$matched = New-Object System.Collections.ArrayList
if ($arch -match 'ARM64') { [void]$reasons.Add("arch=$arch (not declared)") }
if (-not $usernameAscii -or $pathHasSpace -or (($checks | Where-Object { $_.id -eq 'onedrive_redirected' -and $_.status -eq 'warn' }).Count -gt 0)) {
  [void]$matched.Add('P1'); [void]$reasons.Add('complex user path (non-ASCII/space/OneDrive)')
}
if ($networkKind -ne 'direct') {
  [void]$matched.Add('P2'); [void]$reasons.Add("network=$networkKind")
}
$hostProfile = if ($arch -match 'ARM64') { 'out_of_scope' }
  elseif ($matched -contains 'P2') { 'P2' }
  elseif ($matched -contains 'P1') { 'P1' }
  else { 'P0' }

$failCount = ($checks | Where-Object { $_.status -eq 'fail' }).Count
$warnCount = ($checks | Where-Object { $_.status -eq 'warn' }).Count
$preconditionsOk = ($failCount -eq 0)

$result = [pscustomobject][ordered]@{
  schema       = 'paperforge.host-profile/1'
  tool         = 'scripts/host-probe.ps1 v1'
  generated_at = (Get-Date).ToUniversalTime().ToString('o')
  host_profile = $hostProfile
  profile_source = 'v0 (unfrozen)'
  matched_profiles = @($matched)
  reasons      = @($reasons)
  machine      = [pscustomobject][ordered]@{
    os_build         = $osBuild
    os_caption       = $osCaption
    arch             = $arch
    username_ascii   = $usernameAscii
    path_has_space   = $pathHasSpace
    python_source    = $pythonSource
    network_kind     = $networkKind
    defender_only    = $defenderOnly
    free_space_gb    = $freeGb
    long_paths       = ($lp -eq 1)
  }
  preconditions_ok = $preconditionsOk
  checks       = @($checks)
}

$json = $result | ConvertTo-Json -Depth 6
if ($OutFile) {
  $full = [System.IO.Path]::GetFullPath($OutFile)
  [System.IO.File]::WriteAllText($full, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
  Write-Host "host-profile written: $full"
}
Write-Host ("profile={0} preconditions_ok={1} fails={2} warns={3}" -f $hostProfile, $preconditionsOk, $failCount, $warnCount)
Write-Host ($checks | ForEach-Object { "{0,-24} {1,-8} {2}" -f $_.id, $_.status, $_.detail } | Out-String)
$json
