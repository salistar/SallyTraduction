<#
.SYNOPSIS
    SallyTraduction-LLM : traduit un document puis fait relire les phrases signalées par Qwen3-30B-A3B (local).

.DESCRIPTION
    1. SallyTraduction traduit le document (Opus-MT + contrôles) et signale les phrases douteuses ;
    2. le grand modèle Qwen3-30B-A3B (llama.cpp, 100 % local) retraduit ces phrases ;
    3. le document est régénéré avec les corrections : fichier « _FR_LLM » (ou « _EN_LLM »).
    Aucune connexion, aucun droit administrateur. Prérequis : python llm\setup_llm.py (une fois).

.PARAMETER Fichier
    Document PDF ou Word à traduire puis relire.

.PARAMETER Verification
    Ou bien : un fichier *_verification.json existant (document déjà traduit par SallyTraduction).

.PARAMETER Sortie
    Dossier des résultats (défaut : Documents\SallyTraduction).

.PARAMETER Sens
    auto (défaut), en-fr ou fr-en (avec -Fichier).

.PARAMETER Rapide
    Contrôles sans le deuxième avis M2M-100.

.PARAMETER Limite
    Nombre maximal de phrases à relire (pour un essai rapide).

.PARAMETER Threads
    Nombre de cœurs utilisés par le modèle (défaut : la moitié des processeurs logiques).

.EXAMPLE
    .\llm\Relire.ps1 -Fichier "$([Environment]::GetFolderPath('Desktop'))\manuel.pdf"
.EXAMPLE
    .\llm\Relire.ps1 -Verification "C:\docs\Traductions\manuel_FR_verification.json"
#>
[CmdletBinding()]
param(
    [string]$Fichier,
    [string]$Verification,
    [string]$Sortie = (Join-Path ([Environment]::GetFolderPath("MyDocuments")) "SallyTraduction"),
    [ValidateSet("auto", "en-fr", "fr-en")][string]$Sens = "auto",
    [switch]$Rapide,
    [int]$Limite = 0,
    [int]$Threads = 0
)
$ErrorActionPreference = "Stop"
function Terminer([int]$code) { if ($PSCommandPath) { exit $code } else { $global:LASTEXITCODE = $code } }

$Llm = if ($PSScriptRoot) { $PSScriptRoot } else { Join-Path (Get-Location).Path "llm" }
$Racine = Split-Path -Parent $Llm
try {
    if (-not $Fichier -and -not $Verification) { throw "Indiquez -Fichier (document) ou -Verification (fichier *_verification.json)." }
    $py = @((Join-Path $Racine "runtime\python.exe"), (Join-Path $Racine ".venv\Scripts\python.exe")) |
          Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $py) { throw "Python introuvable : suivez le Plan Sally du README (environnement .venv)." }
    if (-not (Test-Path (Join-Path $Llm "bin\llama-server.exe")) -or
        -not (Get-ChildItem (Join-Path $Llm "models") -Filter "*.gguf" -ErrorAction SilentlyContinue)) {
        throw "SallyTraduction-LLM n'est pas installé : lancez  $py llm\setup_llm.py"
    }
    $env:PYTHONPATH = Join-Path $Racine "src"

    # RAM libre : le modèle occupe ≈ 13 Go
    $libre = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1)
    $total = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
    Write-Host ("RAM : {0} Go libres sur {1} Go" -f $libre, $total) -ForegroundColor Cyan
    if ($libre -lt 13) {
        $msg = ("Attention : le modèle utilise ≈ 13 Go. Avec {0} Go libres, Windows lira une partie du modèle sur le disque " +
                "(plus lent). Fermez les applications lourdes (navigateur, Teams, Docker…) pour accélérer.") -f $libre
        Write-Host $msg -ForegroundColor Yellow
    }
    New-Item -ItemType Directory -Force $Sortie | Out-Null

    # 1. Traduction par SallyTraduction (si un document est fourni)
    if ($Fichier) {
        $doc = (Resolve-Path $Fichier).Path
        Write-Host "Étape 1/2 : traduction par SallyTraduction (Opus-MT + contrôles)…" -ForegroundColor Cyan
        $debut = Get-Date
        $a = @("-m", "sally_traduction", "--cli", $doc, "--dir", $Sens, "--out", $Sortie)
        if ($Rapide) { $a += "--fast" }
        & $py @a
        if ($LASTEXITCODE -ne 0) { throw "La traduction a échoué (code $LASTEXITCODE)." }
        $base = [IO.Path]::GetFileNameWithoutExtension($doc)
        $Verification = Get-ChildItem $Sortie -Filter "$base`_*_verification.json" | Where-Object { $_.LastWriteTime -ge $debut -and $_.Name -notmatch "_LLM" } |
                        Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
        if (-not $Verification) { throw "Fichier de vérification introuvable dans $Sortie." }
    }

    # 2. Relecture des phrases signalées par le LLM
    Write-Host "Étape 2/2 : relecture des phrases signalées par Qwen3-30B-A3B (local)…" -ForegroundColor Cyan
    $a = @((Join-Path $Llm "relire.py"), "--verification", (Resolve-Path $Verification).Path, "--sortie", $Sortie)
    if ($Rapide) { $a += "--rapide" }
    if ($Limite -gt 0) { $a += @("--limite", $Limite) }
    if ($Threads -gt 0) { $a += @("--threads", $Threads) }
    & $py @a
    $code = $LASTEXITCODE
    if ($code -eq 0) { Write-Host "Terminé. Résultats dans : $Sortie" -ForegroundColor Green }
    Terminer $code
} catch {
    Write-Host "ERREUR : $($_.Exception.Message)" -ForegroundColor Red
    Terminer 1
}
