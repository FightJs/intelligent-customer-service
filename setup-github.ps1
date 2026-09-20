# setup-github.ps1 — 一次性 GitHub 环境初始化（monorepo 版）
# 前置：代理客户端（Clash 等）运行中，GitHub 规则生效
# 用法：在 A:\Intelligent Customer Service 下执行  .\setup-github.ps1
#
# 适用场景：在新机器上 clone 本仓库后，配置 GitHub CLI + git 凭据 + 上传缓冲。
# 仓库已存在于 GitHub（FightJs/intelligent-customer-service），本脚本不再创建仓库。

$ErrorActionPreference = 'Stop'
$repoRoot = "A:\Intelligent Customer Service"

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
    $ghVer = (& gh --version | Select-Object -First 1)
    Write-Host ("gh 已安装：" + $ghVer) -ForegroundColor Green
} else {
    Write-Host "通过 winget 安装 gh..." -ForegroundColor Yellow
    winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath"
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

Write-Host "`n== 4. 把 gh token 注册为 git HTTPS 凭据助手 ==" -ForegroundColor Cyan
& gh auth setup-git
Write-Host "credential helper 已配置（避免 push 超时）" -ForegroundColor Green

Write-Host "`n== 5. 调小 git 上传缓冲（避免大 push 在代理上挂起）==" -ForegroundColor Cyan
& git config --global http.postBuffer 524288
Write-Host "http.postBuffer = 524288" -ForegroundColor Green

Write-Host "`n== 6. 验证远程仓库连接 ==" -ForegroundColor Cyan
Set-Location $repoRoot
$remote = & git remote get-url origin 2>$null
if ($remote) {
    Write-Host "origin: $remote" -ForegroundColor Green
    & git ls-remote origin *>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ 环境就绪！可用 git pull / push 与 GitHub 同步。" -ForegroundColor Green
        Write-Host "仓库地址：https://github.com/FightJs/intelligent-customer-service" -ForegroundColor Cyan
    } else {
        Write-Host "git ls-remote 失败，请检查凭据与代理" -ForegroundColor Red
    }
} else {
    Write-Host "未检测到 origin 远程。若是新 clone，请确认仓库地址正确。" -ForegroundColor Yellow
    Write-Host "手动添加：git remote add origin https://github.com/FightJs/intelligent-customer-service.git" -ForegroundColor Yellow
}
