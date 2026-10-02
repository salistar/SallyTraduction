# Construit SallyTraduction-Python-Offline.zip : Python embarqué + bibliothèques + modèles + sources.
# Le zip s'utilise sur un PC sans internet, sans installation ni droits administrateur :
#   Expand-Archive SallyTraduction-Python-Offline.zip ; cd SallyTraduction ; .\scripts\Traduire.ps1 …
# Prérequis (PC de construction, avec internet) : Python 3.11 64 bits installé (sert de modèle pour Tcl/Tk),
# modèles présents dans models\ (scripts\setup_models.py --prebuilt).
param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$dist = Join-Path $root "dist-offline"
$out = Join-Path $dist "SallyTraduction"
$rt = Join-Path $out "runtime"

$ver = (& $Python -c "import platform; print(platform.python_version())").Trim()
$base = (& $Python -c "import sys; print(sys.base_prefix)").Trim()
$arch = (& $Python -c "import struct; print(struct.calcsize('P') * 8)").Trim()
if ($arch -ne "64") { throw "Python 64 bits requis" }
$mm = ($ver.Split(".")[0..1] -join "")
foreach ($m in "opus-mt-en-fr-ct2", "opus-mt-fr-en-ct2", "m2m100_418m-ct2", "minilm", "lid") {
    if (-not (Test-Path (Join-Path $root "models\$m"))) { throw "Modèle manquant : models\$m (lancez scripts\setup_models.py --prebuilt)" }
}

Write-Host "1/5  Python $ver embarqué" -ForegroundColor Cyan
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force $rt, (Join-Path $dist "cache") | Out-Null
$embed = Join-Path $dist "cache\python-$ver-embed-amd64.zip"
if (-not (Test-Path $embed)) {
    curl.exe -L --fail -s -o $embed "https://www.python.org/ftp/python/$ver/python-$ver-embed-amd64.zip"
    if ($LASTEXITCODE -ne 0) { throw "Téléchargement du Python embarqué impossible" }
}
Expand-Archive $embed -DestinationPath $rt
# Chemins de recherche du Python embarqué (le fichier ._pth remplace PYTHONPATH)
@("python$mm.zip", ".", "Lib", "Lib\site-packages", "..\src", "import site") |
    Set-Content (Join-Path $rt "python$mm._pth") -Encoding ASCII

Write-Host "2/5  Bibliothèques" -ForegroundColor Cyan
& $Python -m pip install --quiet --disable-pip-version-check --no-warn-script-location `
    --target (Join-Path $rt "Lib\site-packages") -r (Join-Path $root "requirements-runtime.txt")
if ($LASTEXITCODE -ne 0) { throw "Installation des bibliothèques impossible" }

Write-Host "3/5  Tcl/Tk (interface graphique)" -ForegroundColor Cyan
Copy-Item (Join-Path $base "Lib\tkinter") (Join-Path $rt "Lib\tkinter") -Recurse
foreach ($d in "_tkinter.pyd", "tcl86t.dll", "tk86t.dll") { Copy-Item (Join-Path $base "DLLs\$d") $rt }
New-Item -ItemType Directory -Force (Join-Path $rt "tcl") | Out-Null
foreach ($d in "tcl8.6", "tk8.6") { Copy-Item (Join-Path $base "tcl\$d") (Join-Path $rt "tcl\$d") -Recurse }

Write-Host "4/5  Sources, modèles, scripts" -ForegroundColor Cyan
foreach ($d in "src", "models", "tests", "examples", "assets") {
    Copy-Item (Join-Path $root $d) (Join-Path $out $d) -Recurse -Exclude "__pycache__", "out*", "*.png"
}
New-Item -ItemType Directory -Force (Join-Path $out "scripts") | Out-Null
Copy-Item (Join-Path $root "scripts\Traduire.ps1") (Join-Path $out "scripts")
foreach ($f in "LICENSE", "README.md", "GUIDE_UTILISATION.md", "requirements-runtime.txt") { Copy-Item (Join-Path $root $f) $out }
Get-ChildItem $out -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
@"
SallyTraduction - version Python hors ligne (aucune installation, aucun droit administrateur, aucune connexion)

Ouvrez PowerShell dans ce dossier puis :

  Traduire un texte :
    powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Texte "The on-call engineer must approve the change."
  Traduire un fichier :
    powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier "C:\docs\manuel.pdf"
  Traduire un dossier :
    powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier "C:\docs\a_traduire" -Sens en-fr -Rapide
  Ouvrir l'interface :
    powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1
  Utiliser les modèles dans vos scripts Python :
    .\runtime\python.exe examples\utiliser_les_modeles.py

Si les scripts PowerShell sont interdits :
    & ([scriptblock]::Create((Get-Content .\scripts\Traduire.ps1 -Raw))) -Fichier "C:\docs\manuel.pdf"

Résultats : Documents\SallyTraduction (option -Sortie pour changer).
"@ | Set-Content (Join-Path $out "LISEZ-MOI-HORS-LIGNE.txt") -Encoding UTF8

Write-Host "5/5  Archive" -ForegroundColor Cyan
$zip = Join-Path $dist "SallyTraduction-Python-Offline.zip"
& $Python -c @"
import os, zipfile
src, zp = r'$out', r'$zip'
base = os.path.dirname(src)
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for d, _, files in os.walk(src):
        for f in files:
            p = os.path.join(d, f)
            z.write(p, os.path.relpath(p, base).replace(os.sep, '/'))
print('%s : %.0f Mo (dossier décompressé : %.0f Mo)' % (os.path.basename(zp), os.path.getsize(zp) / 2**20,
      sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(src) for f in fs) / 2**20))
"@
