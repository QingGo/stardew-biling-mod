<#
.SYNOPSIS
Stardew Valley Bilingual Text — 构建脚本

.DESCRIPTION
完整构建流程：编译 C# 导出器 → 复制资产列表 → 导出游戏资产 →
构建双语包 → 验证 → 部署到 Mods 目录

.PARAMETER Quick
跳过编译和导出步骤，直接构建双语包
.PARAMETER Deploy
仅部署到 Mods 目录
#>

param(
    [switch]$Quick,
    [switch]$Deploy
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$ModTarget = "D:\steam\steamapps\common\Stardew Valley\Mods\BilingualMod"

if (-not $Quick -and -not $Deploy) {
    # ====== Step 1: 编译 C# 导出器 ======
    Write-Host "=== Step 1: 编译 AssetExporter ===" -ForegroundColor Cyan
    $dotnet = Join-Path $env:TEMP "dotnet6\dotnet.exe"
    if (-not (Test-Path $dotnet)) {
        Write-Host "错误：找不到 .NET 6.0 SDK 在 $dotnet" -ForegroundColor Red
        exit 1
    }
    Push-Location "$ProjectRoot\AssetExporter"
    & $dotnet build --verbosity minimal
    if ($LASTEXITCODE -ne 0) {
        Write-Host "编译失败！" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location

    # ====== Step 2: 复制资产列表 ======
    Write-Host "=== Step 2: 复制 assets-list.txt ===" -ForegroundColor Cyan
    Copy-Item "$ProjectRoot\AssetExporter\assets-list.txt" `
              "D:\steam\steamapps\common\Stardew Valley\Mods\AssetExporter\assets-list.txt" -Force

    # ====== Step 3: 提示运行游戏导出 ======
    Write-Host "=== Step 3: 导出游戏资产 ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "请启动 StardewModdingAPI.exe（游戏窗口会打开），" -ForegroundColor Yellow
    Write-Host "等待 AssetExporter 完成导出，" -ForegroundColor Yellow
    Write-Host "然后关闭游戏窗口。" -ForegroundColor Yellow
    Write-Host ""
    $choice = Read-Host "游戏已导出完成？(y/n)"
    if ($choice -ne 'y' -and $choice -ne 'Y') {
        Write-Host "跳过导出，使用现有导出数据。" -ForegroundColor DarkYellow
    }
}

# ====== Step 4: 构建双语包 ======
if (-not $Deploy) {
    Write-Host "=== Step 4: 构建双语包 ===" -ForegroundColor Cyan
    Push-Location "$ProjectRoot\BilingualModBuilder"
    python build_bilingual_pack.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "构建失败！" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location

    # ====== Step 5: 验证 ======
    Write-Host "=== Step 5: 验证 ===" -ForegroundColor Cyan
    Push-Location $ProjectRoot
    python verify.py --pack
    Pop-Location
}

# ====== Step 6: 部署 ======
Write-Host "=== Step 6: 部署 ===" -ForegroundColor Cyan
Copy-Item -Path "$ProjectRoot\BilingualModBuilder\BilingualMod\*" `
          -Destination $ModTarget `
          -Recurse -Force
Write-Host "已部署到 $ModTarget" -ForegroundColor Green

Write-Host ""
Write-Host "构建完成！" -ForegroundColor Green
Write-Host "启动游戏，将 LanguageMode 切换为 Bilingual 即可测试。" -ForegroundColor Green
