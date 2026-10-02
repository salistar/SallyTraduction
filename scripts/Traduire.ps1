<#
.SYNOPSIS
    Utilise directement les modèles de SallyTraduction avec Python : aucun .exe SallyTraduction, aucune installation,
    aucun droit administrateur, aucune connexion.

.DESCRIPTION
    Python utilisé, dans cet ordre :
      1. runtime\python.exe : Python embarqué du zip hors ligne « SallyTraduction-Python-Offline.zip » ;
      2. .venv\Scripts\python.exe : environnement créé après « git clone » (voir le README, parcours C).
    Modèles : dossier models\ (opus-mt-en-fr-ct2, opus-mt-fr-en-ct2, m2m100_418m-ct2, minilm, lid).

.PARAMETER Fichier
    PDF / Word (.docx), plusieurs fichiers, dossiers ou motifs. Sans -Fichier ni -Texte : ouvre l'interface.

.PARAMETER Texte
    Traduit ce texte et l'affiche (utilisez « - » pour lire l'entrée standard).

.PARAMETER Sens
    auto (défaut), en-fr ou fr-en.

.PARAMETER Sortie
    Dossier des fichiers traduits (défaut : Documents\SallyTraduction).

.PARAMETER Rapide
    Sans le deuxième avis M2M-100 (environ 2 fois plus rapide).

.PARAMETER Interface
    Ouvre l'interface graphique (avec le premier fichier chargé, s'il est donné).

.EXAMPLE
    .\scripts\Traduire.ps1 -Texte "The on-call engineer must approve the change."
.EXAMPLE
    .\scripts\Traduire.ps1 -Fichier "C:\docs\manuel.pdf"
.EXAMPLE
    .\scripts\Traduire.ps1 -Fichier "C:\docs\a_traduire" -Sens en-fr -Rapide
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string[]]$Fichier,
    [string]$Texte,
    [ValidateSet("auto", "en-fr", "fr-en")][string]$Sens = "auto",
    [string]$Sortie = (Join-Path ([Environment]::GetFolderPath("MyDocuments")) "SallyTraduction"),
    [switch]$Rapide,
    [switch]$Interface
)

$ErrorActionPreference = "Stop"

function Terminer([int]$code) { if ($PSCommandPath) { exit $code } else { $global:LASTEXITCODE = $code } }

# Racine du projet : dossier parent de scripts\ (ou dossier courant si le script est exécuté en bloc)
$Racine = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
if (-not (Test-Path (Join-Path $Racine "src\sally_traduction"))) { $Racine = (Get-Location).Path }

try {
    $py = @((Join-Path $Racine "runtime\python.exe"), (Join-Path $Racine ".venv\Scripts\python.exe")) |
          Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $py) {
        throw ("Python introuvable. Utilisez le zip hors ligne (runtime\python.exe) ou créez l'environnement : " +
               "python -m venv .venv ; .\.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt")
    }
    $manquants = "opus-mt-en-fr-ct2", "opus-mt-fr-en-ct2", "minilm", "lid" |
                 Where-Object { -not (Test-Path (Join-Path $Racine "models\$_")) }
    if ($manquants) {
        throw ("Modèles manquants dans models\ : " + ($manquants -join ", ") +
               ". Lancez : $py scripts\setup_models.py --prebuilt")
    }
    $env:PYTHONPATH = Join-Path $Racine "src"
    $tcl = Join-Path $Racine "runtime\tcl"
    if (Test-Path $tcl) {                          # Tcl/Tk du Python embarqué (interface graphique)
        $env:TCL_LIBRARY = Join-Path $tcl "tcl8.6"
        $env:TK_LIBRARY = Join-Path $tcl "tk8.6"
    }

    # ------------------------------------------------------------ traduction d'un texte
    if ($Texte) {
        if ($Texte -eq "-") { $input | & $py -m sally_traduction --texte - --dir $Sens }
        else { & $py -m sally_traduction --texte $Texte --dir $Sens }
        Terminer $LASTEXITCODE
        return
    }

    # ------------------------------------------------------------ interface graphique
    if ($Interface -or -not $Fichier) {
        $pyw = Join-Path (Split-Path -Parent $py) "pythonw.exe"
        $lanceur = if (Test-Path $pyw) { $pyw } else { $py }
        $arg = "-m sally_traduction"
        if ($Fichier) { $arg += " `"$((Resolve-Path $Fichier[0]).Path)`"" }
        Start-Process -FilePath $lanceur -ArgumentList $arg -WorkingDirectory $Racine
        Write-Host "Interface ouverte." -ForegroundColor Green
        Terminer 0
        return
    }

    # ------------------------------------------------------------ traduction de fichiers
    $entrees = foreach ($f in $Fichier) {
        if (Test-Path -LiteralPath $f) { $f } else { $f -split "," | ForEach-Object { $_.Trim().Trim('"') } | Where-Object { $_ } }
    }
    $liste = New-Object System.Collections.Generic.List[string]
    foreach ($f in $entrees) {
        $items = Get-Item -Path $f -ErrorAction SilentlyContinue
        if (-not $items) { Write-Host "Introuvable : $f" -ForegroundColor Yellow; continue }
        foreach ($i in $items) {
            if ($i.PSIsContainer) {
                Get-ChildItem $i.FullName -File | Where-Object {
                    $_.Extension -in ".pdf", ".docx" -and
                    -not (Test-Path (Join-Path $_.DirectoryName ($_.BaseName + "_verification.json")))
                } | ForEach-Object { $liste.Add($_.FullName) }
            } elseif ($i.Extension -in ".pdf", ".docx") { $liste.Add($i.FullName) }
            else { Write-Host "Ignoré (ni PDF ni DOCX) : $($i.FullName)" -ForegroundColor Yellow }
        }
    }
    if ($liste.Count -eq 0) { throw "Aucun fichier PDF ou DOCX à traduire." }
    New-Item -ItemType Directory -Force $Sortie | Out-Null
    $arguments = @("-m", "sally_traduction", "--cli") + $liste + @("--dir", $Sens, "--out", $Sortie)
    if ($Rapide) { $arguments += "--fast" }
    Write-Host ("Python : {0}`nTraduction de {1} fichier(s) vers {2}…" -f $py, $liste.Count, $Sortie) -ForegroundColor Cyan
    $debut = Get-Date
    & $py @arguments
    $code = $LASTEXITCODE
    $couleur = if ($code -eq 0) { "Green" } else { "Red" }
    Write-Host ("Terminé (code {0}) en {1:hh\:mm\:ss}. Résultats dans : {2}" -f $code, ((Get-Date) - $debut), $Sortie) -ForegroundColor $couleur
    Terminer $code
} catch {
    Write-Host "ERREUR : $($_.Exception.Message)" -ForegroundColor Red
    Terminer 1
}
