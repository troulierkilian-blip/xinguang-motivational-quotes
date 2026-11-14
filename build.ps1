$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python 3.11 environment.' }
}
& $taskPython -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $taskPython scripts/build_assets.py
if ($LASTEXITCODE -ne 0) { throw 'Asset validation failed.' }
& $taskPython -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& $taskPython -m PyInstaller --noconfirm '心光.spec'
if ($LASTEXITCODE -ne 0) { throw 'EXE packaging failed.' }
Copy-Item -LiteralPath '使用说明.txt' -Destination 'dist\使用说明.txt' -Force
Copy-Item -LiteralPath 'THIRD_PARTY_NOTICES.md' -Destination 'dist\THIRD_PARTY_NOTICES.md' -Force
Write-Output (Join-Path $PSScriptRoot 'dist\心光.exe')
