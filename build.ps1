# StudyFlow — Release build, Windows x64, Python 3.11
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-Python {
    & python @args
    if ($LASTEXITCODE -ne 0) { throw "Python failed: $LASTEXITCODE" }
}

Invoke-Python -m pip install -r requirements-build.txt
Invoke-Python -m unittest discover -s tests -v
Invoke-Python -m unittest discover -s tests -p gui_acceptance.py -v
Invoke-Python -m PyInstaller --noconfirm --clean --onefile --noupx --windowed --name StudyFlow gui_launcher.py
Invoke-Python -m PyInstaller --noconfirm --clean --onefile --noupx --console --name StudyFlow-CLI main.py

# Smoke tests use a separate database, never a real user's data.
$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("StudyFlow-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    $db = Join-Path $temp "smoke.db"
    @('add Test Build "2026-12-05 18:00"', 'list', 'exit') |
        & ".\dist\StudyFlow-CLI.exe" --db $db
    if ($LASTEXITCODE -ne 0) { throw "CLI startup test failed" }
    Invoke-Python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); assert c.execute('SELECT title FROM tasks').fetchone()==('Build',); c.close()" $db
    $gui = Start-Process -FilePath ".\dist\StudyFlow.exe" -ArgumentList ('--smoke-test --db "' + $db + '"') -PassThru
    if (-not $gui.WaitForExit(60000)) {
        $gui.Kill()
        throw "GUI startup timed out"
    }
    if ($gui.ExitCode -ne 0) { throw "GUI startup test failed: $($gui.ExitCode)" }
} finally {
    Remove-Item -LiteralPath $temp -Recurse -Force
}

$release = Join-Path $PSScriptRoot "release"
New-Item -ItemType Directory -Path $release -Force | Out-Null
$stage = Join-Path $release "StudyFlow"
New-Item -ItemType Directory -Path $stage -Force | Out-Null
Copy-Item -Path @("dist/StudyFlow.exe", "dist/StudyFlow-CLI.exe", "README.md", "DESIGN.md", "INSTALL.txt", "FINAL-CHECK.md") -Destination $stage -Force
$zip = Join-Path $release "StudyFlow-Windows-x64.zip"
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip -Force
# Verify actual archive contents, CRC and Windows PE signatures.
Invoke-Python -c "import sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); assert z.testzip() is None; assert set(z.namelist())=={'StudyFlow.exe','StudyFlow-CLI.exe','README.md','DESIGN.md','INSTALL.txt','FINAL-CHECK.md'}; assert all(z.open(n).read(2)==b'MZ' for n in ('StudyFlow.exe','StudyFlow-CLI.exe')); z.close(); print('ZIP integrity and executable signatures: OK')" $zip
$hash = (Get-FileHash -Path $zip -Algorithm SHA256).Hash.ToLower()
"$hash  StudyFlow-Windows-x64.zip" | Set-Content -Path (Join-Path $release "SHA256SUMS.txt") -Encoding ascii
Write-Host "Release package: $zip"
