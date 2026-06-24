# 启动后端 API（在项目根目录执行）
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = "D:\anaconda3\envs\py312\python.exe"
if (Test-Path "config\local.env") {
    Get-Content "config\local.env" | ForEach-Object {
        if ($_ -match "^PYTHON_PATH=(.+)$") { $Python = $Matches[1].Trim() }
    }
}
& $Python -m pip install -e . -q
& $Python -m sensehub.main
