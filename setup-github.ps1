# setup-github.ps1 — 一次性 GitHub 环境初始化
# 前置：代理客户端（Clash 等）运行中，GitHub 规则生效
# 用法：在 A:\Intelligent Customer Service 下执行  .\setup-github.ps1

$ErrorActionPreference = 'Stop'
$git = "C:\Program Files\Git\cmd\git.exe"
$repoDir = "A:\Intelligent Customer Service\livestream-cs-ui"

Write-Host "== 1. 连通性检查 ==" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "https://api.github.com" -UseBasicParsing -TimeoutSec 15 -Proxy "http://127.0.0.1:7897"
    Write-Host "api.github.com -> $($r.StatusCode) OK" -ForegroundColor Green
} catch {
    Write-Host "代理未通：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host "请先确认 Clash/V2Ray 运行中且 GitHub 规则走有效节点，再重跑本脚本。" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n== 2. 安装 GitHub CLI ==" -ForegroundColor Cyan
$gh = Get-Command gh -ErrorAction SilentlyContinue
if ($gh) {
    Write-Host "gh 已安装：$(& gh --version | Select-Object -First 1)" -ForegroundColor Green
} else {
    Write-Host "通过 winget 安装 gh..." -ForegroundColor Yellow
    winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
    # 刷新当前会话 PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) { Write-Host "gh 安装失败，请手动安装后重跑后续步骤" -ForegroundColor Red; exit 1 }
}

Write-Host "`n== 3. gh 登录（浏览器授权）==" -ForegroundColor Cyan
$status = & gh auth status 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "已登录：$status" -ForegroundColor Green
} else {
    & gh auth login --hostname github.com --git-protocol https --web
    if ($LASTEXITCODE -ne 0) { Write-Host "登录失败" -ForegroundColor Red; exit 1 }
}

Write-Host "`n== 4. 创建 GitHub 私有仓库 livestream-cs-ui ==" -ForegroundColor Cyan
Set-Location $repoDir
$remote = & $git remote get-url origin 2>$null
if ($remote) {
    Write-Host "origin 已存在：$remote" -ForegroundColor Green
} else {
    & gh repo create livestream-cs-ui --private --source=. --remote=origin --description "直播间视觉向量化智能客服 UI 原型"
    Write-Host "仓库已创建并设为 origin" -ForegroundColor Green
}

Write-Host "`n== 5. 推送当前代码 ==" -ForegroundColor Cyan
& $git push -u origin main
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ 完成！仓库地址：" -ForegroundColor Green
    & gh repo view --web
} else {
    Write-Host "推送失败，请检查分支/认证" -ForegroundColor Red
}
