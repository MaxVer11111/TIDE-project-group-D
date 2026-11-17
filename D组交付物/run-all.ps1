$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $tidePython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $tidePython)) {
        throw '请先按03_复现与演示指南.md创建虚拟环境并安装requirements.lock.txt。'
    }
    foreach ($tideScript in @('run_validation.py', 'run_mock.py', 'build_itb_suite.py', 'build_summary.py')) {
        & $tidePython (Join-Path 'src' $tideScript)
        if ($LASTEXITCODE -ne 0) { throw "$tideScript 未通过，退出码 $LASTEXITCODE；请检查新生成证据。" }
    }
} finally {
    Pop-Location
}
