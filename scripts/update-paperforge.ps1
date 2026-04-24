# PaperForge Lite Update Script for Windows
# 一键更新脚本 — 双击运行即可
# 
# 功能：
#   1. 自动检测安装方式（pip/pip-editable/git/zip）
#   2. 执行对应的更新命令
#   3. 如果自动检测失败，提供手动选项
#
# 用法：
#   1. 右键此文件 → "使用 PowerShell 运行"
#   2. 或在终端执行: .\update-paperforge.ps1

param(
    [switch]$Force,      # 跳过确认提示
    [switch]$DryRun      # 只检测不执行
)

$ErrorActionPreference = "Stop"

# 颜色输出
function Write-Color($text, $color = "White") {
    Write-Host $text -ForegroundColor $color
}

Write-Color @"
========================================
  PaperForge Lite 更新助手
========================================
"@ "Cyan"

# 检测 Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Color "[错误] 未找到 Python。请先安装 Python 3.10+" "Red"
    exit 1
}

$pyVersion = & $python.Source --version 2>&1
Write-Color "[检测] Python: $pyVersion" "Gray"

# 检测 pip
$pip = Get-Command pip -ErrorAction SilentlyContinue
if (-not $pip) {
    $pip = Get-Command pip3 -ErrorAction SilentlyContinue
}
if (-not $pip) {
    Write-Color "[错误] 未找到 pip。请检查 Python 安装" "Red"
    exit 1
}

# 检测 paperforge 安装方式
Write-Color "`n[检测] 正在分析 PaperForge 安装方式..." "Yellow"

$installMethod = "unknown"
$installPath = $null

try {
    $pkgPath = & $python.Source -c "import paperforge; print(paperforge.__file__)" 2>$null
    if ($pkgPath) {
        $pkgDir = Split-Path $pkgPath -Parent
        $installPath = $pkgDir
        
        if ($pkgDir -match "site-packages|dist-packages") {
            # pip install (non-editable)
            $installMethod = "pip"
        } elseif (Test-Path (Join-Path $pkgDir "..\.git")) {
            # pip install -e .
            $installMethod = "pip-editable"
            $installPath = Resolve-Path (Join-Path $pkgDir "..") | Select-Object -ExpandProperty Path
        }
    }
} catch {
    # paperforge not installed via pip
}

# 如果上面没检测到，检查当前目录是否有 .git
if ($installMethod -eq "unknown" -and (Test-Path ".git")) {
    $installMethod = "git"
    $installPath = (Get-Location).Path
}

# 显示检测结果
Write-Color "[结果] 安装方式: $installMethod" $(if ($installMethod -ne "unknown") { "Green" } else { "Red" })
if ($installPath) {
    Write-Color "[路径] $installPath" "Gray"
}

if ($DryRun) {
    Write-Color "`n[干运行模式] 仅检测，不执行更新" "Yellow"
    exit 0
}

# 根据安装方式执行更新
$success = $false

switch ($installMethod) {
    "pip" {
        Write-Color "`n[更新] 通过 pip 升级..." "Cyan"
        Write-Color "命令: pip install --upgrade paperforge" "Gray"
        
        if (-not $Force) {
            $confirm = Read-Host "确认更新? [y/N]"
            if ($confirm -notmatch "^[Yy]") {
                Write-Color "[取消] 更新已取消" "Yellow"
                exit 0
            }
        }
        
        & $pip.Source install --upgrade paperforge
        $success = ($LASTEXITCODE -eq 0)
    }
    
    "pip-editable" {
        Write-Color "`n[更新] pip editable 模式 detected" "Cyan"
        Write-Color "步骤 1: git pull 拉取最新代码..." "Yellow"
        
        if (-not $Force) {
            $confirm = Read-Host "确认更新? [y/N]"
            if ($confirm -notmatch "^[Yy]") {
                Write-Color "[取消] 更新已取消" "Yellow"
                exit 0
            }
        }
        
        Push-Location $installPath
        try {
            git pull origin master
            if ($LASTEXITCODE -eq 0) {
                Write-Color "步骤 2: 重新安装 editable 模式..." "Yellow"
                & $pip.Source install -e .
                $success = ($LASTEXITCODE -eq 0)
            }
        } finally {
            Pop-Location
        }
    }
    
    "git" {
        Write-Color "`n[更新] 通过 git pull 更新..." "Cyan"
        Write-Color "命令: git pull origin master" "Gray"
        
        if (-not $Force) {
            $confirm = Read-Host "确认更新? [y/N]"
            if ($confirm -notmatch "^[Yy]") {
                Write-Color "[取消] 更新已取消" "Yellow"
                exit 0
            }
        }
        
        git pull origin master
        $success = ($LASTEXITCODE -eq 0)
    }
    
    default {
        Write-Color "`n[错误] 无法自动检测安装方式" "Red"
        Write-Color @"

可能的解决方案:
1. 如果你是通过 pip 安装的:
   pip install --upgrade paperforge

2. 如果你是通过 git clone 的:
   git pull origin master
   pip install -e .

3. 如果你不确定:
   - 删除现有安装
   - 重新运行: pip install -e .
"@ "Yellow"
        exit 1
    }
}

# 验证更新
if ($success) {
    Write-Color "`n[验证] 检查更新结果..." "Cyan"
    try {
        $newVersion = & $python.Source -c "import paperforge; print(paperforge.__version__)" 2>$null
        Write-Color "[成功] 更新完成！当前版本: $newVersion" "Green"
        Write-Color "`n提示: 请重启 Obsidian 以应用更新" "Yellow"
    } catch {
        Write-Color "[成功] 更新完成！请重启 Obsidian" "Green"
    }
    exit 0
} else {
    Write-Color "`n[失败] 更新过程中出现错误" "Red"
    Write-Color "建议: 检查网络连接，或稍后重试" "Yellow"
    exit 1
}
