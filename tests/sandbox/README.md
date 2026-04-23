# PaperForge Lite — Test Sandbox

## 用途
测试 PaperForge Lite 安装向导 `setup_wizard.py` 的完整流程。

## 目录结构

```
tests/sandbox/
  TestZoteroData/          ← 模拟 Zotero 数据目录（setup wizard 会在 vault 内建 junction 指向这里）
    storage/              ← 5 PDFs（4篇有附件，1篇无）
    zotero.sqlite         ← 伪造（让 Zotero 路径检测通过）
  exports/               ← Better BibTeX JSON 导出（2个域，5篇文献，keys 匹配 storage 文件名）
  00_TestVault/          ← 空目录（安装向导会在这里创建所有子目录）
  README.md              ← 本文件
```

## 测试步骤

```powershell
# 1. 进入仓库根目录
cd D:\...\github-release

# 2. 运行安装向导，指向空 vault（pip install -e . 由向导自动完成）
python setup_wizard.py --vault D:\L\Med\Research\99_System\LiteraturePipeline\github-release\tests\sandbox\00_TestVault

# 3. 安装向导中：
#    - Agent 平台：选你的（opencode / cursor / claude 等）
#    - Zotero 数据目录：填 D:\L\Med\Research\99_System\LiteraturePipeline\github-release\tests\sandbox\TestZoteroData
#      （向导会在 vault 内创建 junction: 00_TestVault/00_System/Zotero -> 指向这里）
#    - BBT 导出目录：填 D:\L\Med\Research\99_System\LiteraturePipeline\github-release\tests\sandbox\exports
#      （向导会检测到 exports/ 下的 JSON 文件）
#    - 其他步骤默认即可

# 4. 测试 pipeline：
cd D:\L\Med\Research\99_System\LiteraturePipeline\github-release\tests\sandbox\00_TestVault
paperforge selection-sync
paperforge index-refresh
paperforge status
```

## 预期结果

| 检查项 | 预期 |
|--------|------|
| wizard 检测 TestZoteroData | 通过（有 storage/ 和 zotero.sqlite）|
| wizard 检测 exports/ | 通过（2个 JSON，keys 有效）|
| selection-sync | 生成 5 条 library-records |
| TSTONE003 ocr_status | nopdf（无 PDF） |
| TSTTWO001/002 有 PDF | ocr_status: pending |

## 注意
- 目录名故意和真实 vault 不同，避免硬编码测试不出来
- PDF 是最小化假文件（pymupdf 可读，内容为空）
- 不要往 sandbox 加真实数据
