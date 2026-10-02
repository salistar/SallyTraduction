# Construit SallyTraduction.exe (PyInstaller) puis l'installateur (Inno Setup).
# Usage : powershell -ExecutionPolicy Bypass -File build\build.ps1 [-SkipInstaller]
param([switch]$SkipInstaller)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"
Set-Location $root

Write-Host "1/3  Icônes et images" -ForegroundColor Cyan
& $py build\make_icon.py

Write-Host "2/3  Exécutable (PyInstaller)" -ForegroundColor Cyan
& $py -m PyInstaller --noconfirm --clean --windowed `
    --name SallyTraduction `
    --icon "$root\assets\icon.ico" `
    --version-file "$root\build\version_info.txt" `
    --paths "$root\src" `
    --add-data "$root\assets;assets" `
    --collect-data customtkinter `
    --collect-all tkinterdnd2 `
    --collect-all ctranslate2 `
    --collect-binaries onnxruntime `
    --hidden-import fasttext_pybind --hidden-import numpy.core --hidden-import numpy.core.multiarray --hidden-import numpy.core._multiarray_umath `
    --exclude-module torch --exclude-module transformers --exclude-module matplotlib `
    --exclude-module scipy --exclude-module pandas --exclude-module IPython --exclude-module pytest `
    --distpath "$root\build\dist" --workpath "$root\build\work" --specpath "$root\build" `
    "$root\build\launcher.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller a échoué" }

if (-not $SkipInstaller) {
    Write-Host "3/3  Installateur (Inno Setup)" -ForegroundColor Cyan
    $iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
              "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) { throw "Inno Setup (ISCC.exe) introuvable" }
    & $iscc /Q "$root\installer\SallyTraduction.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup a échoué" }
    Get-ChildItem "$root\installer\Output\*.exe" | ForEach-Object { "{0}  {1:N0} Mo" -f $_.Name, ($_.Length / 1MB) }
}
