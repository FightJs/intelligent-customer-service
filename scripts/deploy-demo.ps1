# 一键演示部署：本地后端 + cloudflared 快速隧道 + Workers 静态站点
# 用法：powershell -File scripts/deploy-demo.ps1
# 前提：wrangler 已登录（npx wrangler login）；cloudflared 已安装；隧道固定使用 HTTP/2
$ErrorActionPreference = 'Stop'

$root       = Split-Path $PSScriptRoot -Parent
$frontend   = Join-Path $root 'frontend'
$backend    = Join-Path $root 'backend'
$siteOrigin = 'https://livestream-cs-ui.livestream-cs-ui.workers.dev'

# ── 1. 后端（已在跑则复用）────────────────────────────────────
$backendUp = Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 `
    -InformationLevel Quiet -WarningAction SilentlyContinue
if ($backendUp) {
    Write-Host '[1/4] 后端已在 8000 端口运行，复用（注意 CORS 需包含站点域名）'
} else {
    $env:CORS_ORIGINS = "http://localhost:5173,$siteOrigin"
    Start-Process -FilePath 'uv' `
        -ArgumentList 'run','uvicorn','api.app:app','--host','127.0.0.1','--port','8000' `
        -WorkingDirectory $backend -WindowStyle Hidden
    foreach ($i in 1..30) {
        Start-Sleep -Seconds 1
        if (Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 `
                -InformationLevel Quiet -WarningAction SilentlyContinue) { break }
    }
    Write-Host '[1/4] 后端已启动'
}

# ── 2. 隧道（重启拿新 URL）────────────────────────────────────
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
$stamp = Get-Date -Format yyyyMMddHHmmss
$outLog = Join-Path $env:TEMP "cloudflared-$stamp.out.log"
$errLog = Join-Path $env:TEMP "cloudflared-$stamp.err.log"
$tunnelProc = Start-Process -FilePath 'cloudflared' `
    -ArgumentList 'tunnel','--protocol','http2','--url','http://localhost:8000' `
    -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
    -WindowStyle Hidden -PassThru

$tunnelUrl = $null
$tunnelRegistered = $false
foreach ($i in 1..60) {
    Start-Sleep -Seconds 1
    $hit = Select-String -Path $outLog,$errLog `
        -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -List -ErrorAction SilentlyContinue
    if ($hit) { $tunnelUrl = $hit.Matches[0].Value }
    $tunnelRegistered = [bool](Select-String -Path $outLog,$errLog `
        -Pattern 'Registered tunnel connection' -Quiet -ErrorAction SilentlyContinue)
    if ($tunnelUrl -and $tunnelRegistered) { break }
    if ($tunnelProc.HasExited) { break }
}
if (-not $tunnelUrl -or -not $tunnelRegistered) {
    $tail = (Get-Content $errLog -Tail 5 -ErrorAction SilentlyContinue) -join "`n"
    throw "HTTP/2 隧道建立失败。cloudflared 错误日志末尾：`n$tail"
}
Write-Host "[2/4] HTTP/2 隧道已建立：$tunnelUrl"

# ── 3. 构建前端（API 用相对路径 /api，与隧道同域）────────────
$env:VITE_API_BASE = '/api'
Push-Location $frontend
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
    Write-Host '[3/4] 前端构建完成（API 走同域相对路径）'
} finally { Pop-Location }

# ── 4. 重启后端加载最新 dist ──────────────────────────────────
$backendProc = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'uvicorn' }
if ($backendProc) {
    $backendProc | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Start-Sleep -Seconds 2
}
$env:CORS_ORIGINS = "http://localhost:5173,$siteOrigin"
Start-Process -FilePath 'uv' `
    -ArgumentList 'run','uvicorn','api.app:app','--host','127.0.0.1','--port','8000' `
    -WorkingDirectory $backend -WindowStyle Hidden
foreach ($i in 1..30) {
    Start-Sleep -Seconds 1
    if (Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 `
            -InformationLevel Quiet -WarningAction SilentlyContinue) { break }
}
Write-Host '[4/4] 后端已加载最新前端并启动'

Write-Host ''
Write-Host "部署完成，访问入口（前后端同域，国内直连）：$tunnelUrl"
Write-Host "Workers 镜像（需梯子）：$siteOrigin"
Write-Host '注意：电脑关机或断网后服务即不可用，重新运行本脚本恢复。'
