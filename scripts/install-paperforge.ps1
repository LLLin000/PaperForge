param([switch]$Force)

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/LLLin000/PaperForge.git"

Write-Host "=== PaperForge Lite 一键安装 ===" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
try {
    $py = (Get-Command python -ErrorAction Stop).Source
    Write-Host "[OK] Python: $((python --version))" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] 未找到 Python，请先安装 https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# 检查 pip
try {
    python -m pip --version >$null 2>&1
    Write-Host "[OK] pip 可用" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] pip 不可用，请检查 Python 安装" -ForegroundColor Red
    exit 1
}

# 检查是否已安装
$installed = $false
try {
    $ver = python -c "import paperforge; print('ok')" 2>$null
    if ($ver -eq "ok") { $installed = $true }
} catch {}

if ($installed -and -not $Force) {
    $current = python -c "import json, urllib.request; r=json.loads(urllib.request.urlopen('https://api.github.com/repos/LLLin000/PaperForge/releases/latest').read()); print(r['tag_name'])" 2>$null
    Write-Host "[i] 已安装 ($current). 使用 -Force 参数重新安装" -ForegroundColor Yellow
    Write-Host "    更新命令: paperforge update" -ForegroundColor Yellow
    exit 0
}

Write-Host "正在安装 PaperForge Lite..." -ForegroundColor Yellow
python -m pip install "git+$RepoUrl" --upgrade
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] 安装失败" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] 安装成功!" -ForegroundColor Green
Write-Host ""

# 验证
try {
    python -c "import paperforge; print(f'PaperForge Lite {paperforge.__version__}')" 2>$null
} catch {
    python -c "import paperforge; print('PaperForge Lite 已安装')"
}

Write-Host ""
Write-Host "下一步: 运行 setup 向导配置你的 Vault" -ForegroundColor Cyan
Write-Host "  paperforge setup" -ForegroundColor White
Write-Host ""
Write-Host "常用命令:" -ForegroundColor Cyan
Write-Host "  paperforge sync       同步 Zotero" -ForegroundColor White
Write-Host "  paperforge ocr        运行 OCR" -ForegroundColor White
Write-Host "  paperforge update     检查更新" -ForegroundColor White
Write-Host ""
