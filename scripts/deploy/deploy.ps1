# 从 Windows / Cursor 一键部署到阿里云 Ubuntu 轻量服务器
# 用法:
#   1. 复制 scripts/deploy/target.env.example -> scripts/deploy/target.env 并填写 IP
#   2. 确保 config/local.env 已填好 API Key、SMTP、JWT_SECRET 等
#   3. 在项目根目录: .\scripts\deploy\deploy.ps1

param(
    [string]$ServerHost = "",
    [string]$ServerUser = "root",
    [string]$Domain = "",
    [string]$SshKey = "",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root

$TargetFile = Join-Path $PSScriptRoot "target.env"
if (Test-Path $TargetFile) {
    Get-Content $TargetFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
        $k, $v = $_ -split '=', 2
        $k = $k.Trim(); $v = $v.Trim()
        switch ($k) {
            "SERVER_HOST" { if (-not $ServerHost) { $ServerHost = $v } }
            "SERVER_USER" { if ($ServerUser -eq "root") { $ServerUser = $v } }
            "DOMAIN"      { if (-not $Domain) { $Domain = $v } }
            "SSH_KEY"     { if (-not $SshKey) { $SshKey = $v } }
        }
    }
}

if (-not $ServerHost) {
    Write-Host "请填写 SERVER_HOST：编辑 scripts/deploy/target.env 或传参 -ServerHost" -ForegroundColor Red
    exit 1
}
if (-not $Domain) { $Domain = $ServerHost }

$LocalEnv = Join-Path $Root "config\local.env"
if (-not (Test-Path $LocalEnv)) {
    Write-Host "缺少 config/local.env，请先复制 local.env.example 并填写密钥。" -ForegroundColor Red
    exit 1
}

$sshArgs = @()
if ($SshKey -and (Test-Path $SshKey)) {
    $sshArgs += @("-i", $SshKey)
}
$Remote = "${ServerUser}@${ServerHost}"

function Invoke-Ssh([string]$Cmd) {
    & ssh @sshArgs -o StrictHostKeyChecking=accept-new $Remote $Cmd
    if ($LASTEXITCODE -ne 0) { throw "SSH 失败: $Cmd" }
}

function Invoke-Scp([string]$Local, [string]$RemotePath) {
    & scp @sshArgs -o StrictHostKeyChecking=accept-new -r $Local "${Remote}:${RemotePath}"
    if ($LASTEXITCODE -ne 0) { throw "SCP 失败: $Local" }
}

Write-Host "==> 测试 SSH 连接 $Remote ..." -ForegroundColor Cyan
Invoke-Ssh "echo ok"

if (-not $SkipBuild) {
    Write-Host "==> 本地构建前端 (npm run build) ..." -ForegroundColor Cyan
    Push-Location (Join-Path $Root "web")
    if (-not (Test-Path "node_modules")) { npm ci }
    npm run build
    Pop-Location
}

Write-Host "==> 打包并上传项目到 /opt/sensehub ..." -ForegroundColor Cyan
Invoke-Ssh "mkdir -p /opt/sensehub"

$excludeList = @(
    ".git", "node_modules", "web/node_modules", ".venv",
    "agent-example", "skills-example", "__pycache__", ".cursor", "SenseHubData"
)
$tarArgs = $excludeList | ForEach-Object { "--exclude=$_" }
& tar -czf - @tarArgs -C $Root . | & ssh @sshArgs -o StrictHostKeyChecking=accept-new $Remote "cd /opt/sensehub && tar xzf -"
if ($LASTEXITCODE -ne 0) { throw "上传失败" }

Write-Host "==> 上传 config/local.env（含密钥，单独传输）..." -ForegroundColor Cyan
Invoke-Scp $LocalEnv "/opt/sensehub/config/local.env"

Write-Host "==> 远程安装依赖与服务 ..." -ForegroundColor Cyan
$setupScript = (Get-Content (Join-Path $PSScriptRoot "ubuntu_setup.sh") -Raw) -replace "`r`n", "`n"
$setupB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($setupScript))
Invoke-Ssh "echo $setupB64 | base64 -d > /tmp/sensehub_setup.sh && chmod +x /tmp/sensehub_setup.sh && APP_ROOT=/opt/sensehub DOMAIN=$Domain SKIP_NPM_BUILD=1 bash /tmp/sensehub_setup.sh"

Write-Host ""
Write-Host "部署完成！" -ForegroundColor Green
Write-Host "  访问: http://${Domain}/"
Write-Host "  健康: http://${Domain}/health"
Write-Host "  若无法访问，请在阿里云轻量防火墙放行 80/443 端口。"
Write-Host "  查看日志: ssh $Remote journalctl -u sensehub -f"
