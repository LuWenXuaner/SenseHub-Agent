# Pre-commit secret scan for SenseHub Agent (core project only)
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$patterns = @(
    'sk-[a-zA-Z0-9]{16,}',
    'ark-[a-f0-9-]{20,}',
    'SILICONFLOW_API_KEY\s*=\s*[^\s#]+',
    'VOLCENGINE_API_KEY\s*=\s*[^\s#]+',
    'JWT_SECRET\s*=\s*[^\s#]+',
    'GITHUB_OAUTH_CLIENT_SECRET\s*=\s*[^\s#]+',
    'WECHAT_OAUTH_APP_SECRET\s*=\s*[^\s#]+'
)

$blockedFiles = @(
    'config\local.env',
    'config\paths.yaml',
    'config\policies.yaml',
    '.env'
)

$scanRoots = @(
    'sensehub',
    'web\src',
    'web\public',
    'config',
    'scripts',
    'docs'
)

$skipFileNames = @(
    'local.env',
    'paths.yaml',
    'policies.yaml'
)

$failed = $false

Write-Host "SenseHub secret scan"
Write-Host "Root: $repoRoot"

foreach ($rel in $blockedFiles) {
    $full = Join-Path $repoRoot $rel
    if (-not (Test-Path $full)) { continue }
    if (-not (Test-Path (Join-Path $repoRoot '.git'))) {
        Write-Host "[WARN] Sensitive file on disk (ensure .gitignore before git init): $rel"
        continue
    }
    git -C $repoRoot ls-files --error-unmatch $rel 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[FAIL] Tracked by git: $rel"
        $failed = $true
    }
}

foreach ($scanRoot in $scanRoots) {
    $base = Join-Path $repoRoot $scanRoot
    if (-not (Test-Path $base)) { continue }
    $files = Get-ChildItem -Path $base -Recurse -File -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        if ($skipFileNames -contains $file.Name) { continue }
        if ($file.Name -match '\.example$') { continue }

        $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
        if (-not $content) { continue }

        foreach ($pat in $patterns) {
            if ($content -match $pat) {
                $hit = $Matches[0]
                if ($hit -match '=\s*$' -or $hit -match 'change-me') { continue }
                Write-Host "[FAIL] $($file.FullName) matched secret pattern"
                $failed = $true
                break
            }
        }
    }
}

if ($failed) {
    Write-Host ""
    Write-Host "Scan failed. Keep config/local.env gitignored and rotate exposed keys."
    exit 1
}

Write-Host ""
Write-Host "Scan passed."
exit 0
