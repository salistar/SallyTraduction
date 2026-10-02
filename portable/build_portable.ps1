# Construit SallyTraduction.exe portable : lanceur C# + ZIP (application PyInstaller + modèles) ajouté en fin de fichier.
# Prérequis : build\dist\SallyTraduction (lancer d'abord build\build.ps1 -SkipInstaller).
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$here = $PSScriptRoot
$dist = Join-Path $root "build\dist\SallyTraduction"
$out = Join-Path $here "Output"
New-Item -ItemType Directory -Force $out | Out-Null
if (-not (Test-Path "$dist\SallyTraduction.exe")) { throw "Exécutable introuvable : lancez build\build.ps1 -SkipInstaller" }
if (Test-Path "$dist\models") { throw "Le dossier dist contient un lien 'models' de test : supprimez-le (rmdir)" }

Write-Host "1/3  Archive de l'application et des modèles" -ForegroundColor Cyan
$zip = Join-Path $here "payload.zip"
& (Join-Path $root ".venv\Scripts\python.exe") -c @"
import os, zipfile
dist, models, zp = r'$dist', r'$root\models', r'$zip'
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for base, prefix in ((dist, ''), (models, 'models/')):
        for d, _, files in os.walk(base):
            for f in files:
                p = os.path.join(d, f)
                z.write(p, prefix + os.path.relpath(p, base).replace(os.sep, '/'))
print('archive : %.0f Mo' % (os.path.getsize(zp) / 2**20))
"@

Write-Host "2/3  Lanceur C#" -ForegroundColor Cyan
$csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$stub = Join-Path $here "stub.exe"
& $csc /nologo /target:winexe /optimize+ /platform:x64 "/win32icon:$root\assets\icon.ico" "/out:$stub" `
    /r:System.IO.Compression.dll /r:System.IO.Compression.FileSystem.dll /r:System.Windows.Forms.dll /r:System.Drawing.dll `
    (Join-Path $here "Launcher.cs")
if ($LASTEXITCODE -ne 0) { throw "Compilation du lanceur échouée" }

Write-Host "3/3  Assemblage" -ForegroundColor Cyan
$final = Join-Path $out "SallyTraduction.exe"
$o = [IO.File]::Create($final)
try {
    $s = [IO.File]::OpenRead($stub); $s.CopyTo($o); $s.Close()
    $offset = $o.Position
    $z = [IO.File]::OpenRead($zip); $z.CopyTo($o); $len = $z.Length; $z.Close()
    $o.Write([BitConverter]::GetBytes([long]$offset), 0, 8)
    $o.Write([BitConverter]::GetBytes([long]$len), 0, 8)
    $o.Write([Text.Encoding]::ASCII.GetBytes("SALLYPK1"), 0, 8)
} finally { $o.Close() }
Remove-Item $zip, $stub
"{0}  {1:N0} Mo" -f $final, ((Get-Item $final).Length / 1MB)
