<#
.SYNOPSIS
    SallyTraduction en ligne de commande PowerShell : sans installation, sans droits administrateur, hors ligne.

.DESCRIPTION
    Utilise l'exécutable portable SallyTraduction-Portable.exe :
      - trouvé à côté de ce script, dans le dossier courant ou dans %LOCALAPPDATA%\SallyTraduction ;
      - ou indiqué avec -Exe (par exemple sur une clé USB) ;
      - ou, s'il y a internet, téléchargé depuis GitHub (empreinte SHA-256 vérifiée).
    Au premier usage, l'application est décompressée une seule fois dans le profil utilisateur.
    Rien n'est écrit dans Program Files ni dans le registre.

.PARAMETER Fichier
    Un ou plusieurs PDF / Word (.docx), dossiers (tous les PDF et DOCX qu'ils contiennent) ou motifs (*.pdf).
    Sans fichier : ouvre l'interface graphique.

.PARAMETER Sens
    auto (défaut), en-fr ou fr-en.

.PARAMETER Sortie
    Dossier des fichiers traduits (défaut : Documents\SallyTraduction).

.PARAMETER Rapide
    Sans le deuxième avis M2M-100 (environ 2 fois plus rapide).

.PARAMETER Exe
    Chemin de SallyTraduction-Portable.exe (clé USB, partage réseau…).

.PARAMETER Interface
    Ouvre l'interface graphique (avec le premier fichier déjà chargé, s'il est donné).

.PARAMETER Nettoyer
    Supprime l'application décompressée et l'exécutable téléchargé (le glossaire est conservé).

.EXAMPLE
    .\SallyTraduction.ps1 -Fichier "C:\docs\manuel.pdf"
.EXAMPLE
    .\SallyTraduction.ps1 -Fichier "C:\docs\a_traduire" -Sens en-fr -Sortie "C:\docs\traductions" -Rapide
.EXAMPLE
    .\SallyTraduction.ps1 -Exe "E:\SallyTraduction-Portable.exe" -Fichier "C:\docs\guide.docx"
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string[]]$Fichier,
    [ValidateSet("auto", "en-fr", "fr-en")][string]$Sens = "auto",
    [string]$Sortie = (Join-Path ([Environment]::GetFolderPath("MyDocuments")) "SallyTraduction"),
    [switch]$Rapide,
    [string]$Exe,
    [switch]$Interface,
    [switch]$Nettoyer
)

$ErrorActionPreference = "Stop"
$NomExe = "SallyTraduction-Portable.exe"
$Depot = "https://github.com/salistar/SallyTraduction/releases/latest/download"
$Cache = Join-Path $env:LOCALAPPDATA "SallyTraduction"

function Ecrire($texte, $couleur = "Gray") { Write-Host $texte -ForegroundColor $couleur }

function Terminer([int]$code) {
    # Lancé avec -File ou .\script.ps1 : code de sortie du processus ; lancé en bloc de script : $LASTEXITCODE
    if ($PSCommandPath) { exit $code } else { $global:LASTEXITCODE = $code }
}

function Dossiers-Base {
    @($env:LOCALAPPDATA, [IO.Path]::GetTempPath(), $(if ($Exe) { Split-Path -Parent $Exe })) | Where-Object { $_ }
}

# ------------------------------------------------------------------ nettoyage
if ($Nettoyer) {
    foreach ($b in Dossiers-Base) {
        $d = Join-Path $b "SallyTraduction"
        Get-ChildItem $d -Directory -Filter "app-*" -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-Item $_.FullName -Recurse -Force; Ecrire "Supprimé : $($_.FullName)"
        }
    }
    $telecharge = Join-Path $Cache $NomExe
    if (Test-Path $telecharge) { Remove-Item $telecharge -Force; Ecrire "Supprimé : $telecharge" }
    Ecrire "Nettoyage terminé (glossaire conservé dans %APPDATA%\SallyTraduction)." Green
    return
}

# ------------------------------------------------------------------ exécutable portable
function Trouver-Exe {
    if ($Exe) {
        if (-not (Test-Path $Exe)) { throw "Exécutable introuvable : $Exe" }
        return (Resolve-Path $Exe).Path
    }
    $candidats = @()
    if ($PSScriptRoot) { $candidats += (Join-Path $PSScriptRoot $NomExe) }
    $candidats += (Join-Path (Get-Location).Path $NomExe), (Join-Path $Cache $NomExe)
    foreach ($c in $candidats) { if (Test-Path $c) { return $c } }
    return $null
}

function Telecharger-Exe {
    New-Item -ItemType Directory -Force $Cache | Out-Null
    $dest = Join-Path $Cache $NomExe
    $tmp = "$dest.part"
    Ecrire "Téléchargement de $NomExe (≈ 730 Mo) depuis GitHub…" Cyan
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        & $curl.Source -L --fail --progress-bar -o $tmp "$Depot/$NomExe"
        if ($LASTEXITCODE -ne 0) { throw "Échec du téléchargement (pas d'internet ?)" }
    } else {
        (New-Object Net.WebClient).DownloadFile("$Depot/$NomExe", $tmp)
    }
    try {
        $sommes = (New-Object Net.WebClient).DownloadString("$Depot/SHA256SUMS.txt")
        $attendu = ($sommes -split "`n" | Where-Object { $_ -match [regex]::Escape($NomExe) } | Select-Object -First 1) -replace "\s.*$", ""
        $obtenu = (Get-FileHash $tmp -Algorithm SHA256).Hash
        if ($attendu -and $attendu.Trim().ToUpper() -ne $obtenu) { Remove-Item $tmp -Force; throw "Empreinte SHA-256 incorrecte : fichier corrompu." }
        if ($attendu) { Ecrire "Empreinte SHA-256 vérifiée." Green }
    } catch [System.Net.WebException] { Ecrire "Empreinte SHA-256 non vérifiée (fichier SHA256SUMS.txt indisponible)." Yellow }
    Move-Item $tmp $dest -Force
    return $dest
}

try {
    $portable = Trouver-Exe
    if (-not $portable) { $portable = Telecharger-Exe }
    Ecrire "Exécutable : $portable"

    # Décompression unique (fenêtre de progression au premier lancement), puis chemin de l'application
    $fic = [IO.Path]::GetTempFileName()
    $p = Start-Process -FilePath $portable -ArgumentList "--prepare", "`"$fic`"" -Wait -PassThru
    $racine = (Get-Content $fic -Raw -ErrorAction SilentlyContinue)
    Remove-Item $fic -Force -ErrorAction SilentlyContinue
    if ($p.ExitCode -ne 0 -or -not $racine) { throw "Préparation de l'application impossible (code $($p.ExitCode))." }
    $app = Join-Path $racine.Trim() "SallyTraduction.exe"
    if (-not (Test-Path $app)) { throw "Application introuvable après préparation : $app" }

    # ---------------------------------------------------------------- interface graphique
    if ($Interface -or -not $Fichier) {
        $args0 = if ($Fichier) { "`"$((Resolve-Path $Fichier[0]).Path)`"" } else { $null }
        if ($args0) { Start-Process -FilePath $app -ArgumentList $args0 } else { Start-Process -FilePath $app }
        Ecrire "Interface ouverte." Green
        Terminer 0
        return
    }

    # ---------------------------------------------------------------- traduction en ligne de commande
    $liste = New-Object System.Collections.Generic.List[string]
    # Avec « powershell -File », une liste "a.pdf","b.docx" arrive en une seule chaîne « a.pdf,b.docx »
    $entrees = foreach ($f in $Fichier) {
        if (Test-Path -LiteralPath $f) { $f } else { $f -split "," | ForEach-Object { $_.Trim().Trim('"') } | Where-Object { $_ } }
    }
    foreach ($f in $entrees) {
        $items = Get-Item -Path $f -ErrorAction SilentlyContinue
        if (-not $items) { Ecrire "Introuvable : $f" Yellow; continue }
        foreach ($i in $items) {
            if ($i.PSIsContainer) {
                # Les résultats d'une traduction précédente (accompagnés de leur *_verification.json) sont ignorés
                Get-ChildItem $i.FullName -File | Where-Object {
                    $_.Extension -in ".pdf", ".docx" -and
                    -not (Test-Path (Join-Path $_.DirectoryName ($_.BaseName + "_verification.json")))
                } | ForEach-Object { $liste.Add($_.FullName) }
            } elseif ($i.Extension -in ".pdf", ".docx") { $liste.Add($i.FullName) }
            else { Ecrire "Ignoré (ni PDF ni DOCX) : $($i.FullName)" Yellow }
        }
    }
    if ($liste.Count -eq 0) { throw "Aucun fichier PDF ou DOCX à traduire." }
    New-Item -ItemType Directory -Force $Sortie | Out-Null

    $arguments = "--cli " + (($liste | ForEach-Object { "`"$_`"" }) -join " ") + " --dir $Sens --out `"$Sortie`""
    if ($Rapide) { $arguments += " --fast" }
    Ecrire ("Traduction de {0} fichier(s) vers {1}…" -f $liste.Count, $Sortie) Cyan
    $debut = Get-Date
    $p = Start-Process -FilePath $app -ArgumentList $arguments -Wait -NoNewWindow -PassThru
    $duree = (Get-Date) - $debut
    if ($p.ExitCode -eq 0) {
        Ecrire ("Terminé en {0:hh\:mm\:ss}. Résultats dans : {1}" -f $duree, $Sortie) Green
    } else {
        Ecrire ("Terminé avec des erreurs (code {0}) en {1:hh\:mm\:ss}." -f $p.ExitCode, $duree) Red
    }
    Terminer $p.ExitCode
} catch {
    Ecrire "ERREUR : $($_.Exception.Message)" Red
    if ($_.Exception.Message -match "internet|téléchargement") {
        Ecrire "Sans internet : copiez $NomExe à côté de ce script, ou indiquez-le avec -Exe." Yellow
    }
    Terminer 1
}
