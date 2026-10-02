# SallyTraduction 1.1 : traduction technique locale FR ↔ EN

## ⬇️ Téléchargements (dernière version)

| | Lien de téléchargement direct | Taille |
|---|---|---|
| 💼 **Exécutable portable** (sans installation, sans droits administrateur) | **[SallyTraduction-Portable.exe](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Portable.exe)** | **730 Mo** |
| 🧩 **Installateur Windows** (raccourcis, menu Démarrer, clic droit) | **[SallyTraduction-Setup.exe](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Setup.exe)** | **693 Mo** |
| ⌨️ **Script PowerShell** (traduire en ligne de commande, sans installation) | **[SallyTraduction.ps1](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction.ps1)** | 9 Ko |

**Exécutable portable :** `https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Portable.exe`

**Installateur :** `https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Setup.exe`

> **Fonctionne sans internet et sans Ollama** : téléchargez le fichier une fois, puis copiez-le (clé USB) sur l'ordinateur hors ligne. Tous les modèles sont inclus.
> Ces liens pointent toujours vers la dernière version. Empreintes SHA-256 : [SHA256SUMS.txt](https://github.com/salistar/SallyTraduction/releases/latest/download/SHA256SUMS.txt).

## 🚀 Tout depuis `git clone`, commande par commande

Toutes les commandes se tapent dans **PowerShell**, ouvert normalement (menu Démarrer → « PowerShell », **sans** « Exécuter en tant qu'administrateur »). Aucune n'exige de droits administrateur.

### Parcours A : utiliser l'application (sans rien compiler)

**Prérequis :** Windows 10/11 64 bits, 8 Go de RAM (16 Go conseillés), 2 Go libres, processeur AVX2. Git est facultatif (voir l'étape 1 bis).

```powershell
# 1. Récupérer le projet
git clone https://github.com/salistar/SallyTraduction.git

# 2. Entrer dans le dossier
cd SallyTraduction

# 3. Télécharger l'exécutable portable (730 Mo) à côté du script
curl.exe -L -o scripts\SallyTraduction-Portable.exe https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Portable.exe

# 4. (conseillé) Vérifier son empreinte : comparer avec la ligne « SallyTraduction-Portable.exe » de SHA256SUMS.txt
Get-FileHash scripts\SallyTraduction-Portable.exe -Algorithm SHA256
curl.exe -L https://github.com/salistar/SallyTraduction/releases/latest/download/SHA256SUMS.txt

# 5. Tester sur le petit document Word fourni (résultat dans Documents\SallyTraduction)
powershell -ExecutionPolicy Bypass -File scripts\SallyTraduction.ps1 -Fichier tests\Helios_Guide_EN.docx

# 6. Traduire vos documents
powershell -ExecutionPolicy Bypass -File scripts\SallyTraduction.ps1 -Fichier "C:\docs\manuel.pdf"
powershell -ExecutionPolicy Bypass -File scripts\SallyTraduction.ps1 -Fichier "C:\docs\a_traduire" -Sens en-fr -Sortie "C:\docs\traductions"

# 7. Ou ouvrir l'interface graphique
powershell -ExecutionPolicy Bypass -File scripts\SallyTraduction.ps1

# 8. Relire les phrases signalées (page / ligne / mot) : dans l'interface, « Reprendre une vérification… »
#    puis choisir le fichier *_verification.json créé à côté du document traduit.

# 9. (facultatif) Tout supprimer de l'ordinateur ; le glossaire %APPDATA%\SallyTraduction est conservé
powershell -ExecutionPolicy Bypass -File scripts\SallyTraduction.ps1 -Nettoyer
```

**1 bis. Sans Git :** remplacez les étapes 1 et 2 par :
```powershell
curl.exe -L -o SallyTraduction.zip https://github.com/salistar/SallyTraduction/archive/refs/heads/main.zip
Expand-Archive SallyTraduction.zip -DestinationPath .
cd SallyTraduction-main
```

**Ordinateur sans internet :** faites les étapes 1 à 4 sur un PC connecté, copiez **tout le dossier `SallyTraduction`** sur une clé USB, puis sur le PC hors ligne :
```powershell
cd E:\SallyTraduction
powershell -ExecutionPolicy Bypass -File scripts\SallyTraduction.ps1 -Fichier tests\Helios_Guide_EN.docx
powershell -ExecutionPolicy Bypass -File scripts\SallyTraduction.ps1 -Fichier "C:\docs\manuel.pdf"
```
Le premier lancement prépare l'application dans `%LOCALAPPDATA%\SallyTraduction` (≈ 30 s, une seule fois). Ensuite, plus aucun accès réseau n'a lieu.

**Scripts PowerShell interdits par l'entreprise ?** Cette forme passe toujours, car le contenu du script est lu comme du texte :
```powershell
& ([scriptblock]::Create((Get-Content .\scripts\SallyTraduction.ps1 -Raw))) -Fichier "C:\docs\manuel.pdf"
```

### Parcours B : reconstruire depuis les sources

**Prérequis, tous installables sans droits administrateur :**
| Outil | Installation pour l'utilisateur courant |
|---|---|
| Git | `winget install Git.Git --scope user`, ou [Git portable](https://git-scm.com/download/win) |
| Python **3.11** 64 bits | `winget install Python.Python.3.11 --scope user`, ou l'installateur de python.org avec « Install for me only » |
| Inno Setup 6 (installateur seulement) | `winget install JRSoftware.InnoSetup --scope user` |
| Compilateur C# (version portable) | déjà présent dans Windows (.NET Framework 4.8) |

```powershell
# 1. Récupérer le projet
git clone https://github.com/salistar/SallyTraduction.git

# 2. Entrer dans le dossier
cd SallyTraduction

# 3. Créer l'environnement Python du projet
python -m venv .venv

# 4. Mettre pip à jour
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# 5. Installer les dépendances de l'application et de la construction
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 6. Installer les outils de conversion des modèles (≈ 300 Mo, utilisés seulement à l'étape 7)
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install transformers huggingface_hub

# 7. Télécharger et convertir les 5 modèles dans models\ (≈ 3 Go téléchargés la première fois, puis 750 Mo sur disque)
.\.venv\Scripts\python.exe scripts\setup_models.py

# 8. Lancer l'application depuis les sources
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m sally_traduction

# 9. Tester la ligne de commande depuis les sources
.\.venv\Scripts\python.exe -m sally_traduction --cli tests\Helios_Guide_EN.docx tests\Helios_EN_20p.pdf --fast --out "$env:TEMP\sally-test"

# 10. (facultatif) Générer le document de test de 500 pages dans benchmark\00-Document-Test\
.\.venv\Scripts\python.exe benchmark\00-Document-Test\generate_test_pdf.py

# 11. Construire l'exécutable (build\dist\SallyTraduction\)
powershell -ExecutionPolicy Bypass -File build\build.ps1 -SkipInstaller

# 12. Construire la version portable en un seul .exe (portable\Output\SallyTraduction.exe)
powershell -ExecutionPolicy Bypass -File portable\build_portable.ps1

# 13. (facultatif) Construire aussi l'installateur (installer\Output\SallyTraduction-Setup-<version>.exe)
powershell -ExecutionPolicy Bypass -File build\build.ps1

# 14. Utiliser votre propre portable avec le script
powershell -ExecutionPolicy Bypass -File scripts\SallyTraduction.ps1 -Exe portable\Output\SallyTraduction.exe -Fichier tests\Helios_Guide_EN.docx
```

## ⌨️ Utiliser l'application uniquement avec PowerShell (sans installation, sans droits administrateur)

Aucune installation, aucun droit administrateur, rien dans Program Files ni dans le registre : le script utilise l'exécutable portable, qui se prépare une seule fois dans votre profil (`%LOCALAPPDATA%\SallyTraduction`). Ouvrez **PowerShell** (menu Démarrer → « PowerShell », sans « Exécuter en tant qu'administrateur »).

### Cas 1 : ordinateur **avec** internet
Une seule commande ouvre l'application (téléchargement automatique au premier usage, empreinte SHA-256 vérifiée) :
```powershell
irm https://raw.githubusercontent.com/salistar/SallyTraduction/main/scripts/SallyTraduction.ps1 | iex
```
Traduire directement un fichier, sans ouvrir l'interface :
```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/salistar/SallyTraduction/main/scripts/SallyTraduction.ps1))) -Fichier "C:\docs\manuel.pdf"
```

### Cas 2 : ordinateur **sans** internet (clé USB)
1. Sur un PC connecté, téléchargez **[SallyTraduction-Portable.exe](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Portable.exe)** et **[SallyTraduction.ps1](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction.ps1)**, puis copiez-les **dans le même dossier** de la clé USB (par exemple `E:\SallyTraduction\`).
2. Sur le PC hors ligne, dans PowerShell :
```powershell
cd E:\SallyTraduction
powershell -ExecutionPolicy Bypass -File .\SallyTraduction.ps1 -Fichier "C:\docs\manuel.pdf"
```
`-ExecutionPolicy Bypass` ne vaut que pour cette commande : **aucun droit administrateur requis**, aucun réglage modifié.
Si l'entreprise interdit tout script, cette variante passe quand même, car le contenu est lu comme du texte :
```powershell
& ([scriptblock]::Create((Get-Content E:\SallyTraduction\SallyTraduction.ps1 -Raw))) -Fichier "C:\docs\manuel.pdf"
```

### Commandes utiles
| Besoin | Commande (depuis le dossier du script) |
|---|---|
| Ouvrir l'interface graphique | `.\SallyTraduction.ps1` |
| Traduire un fichier | `.\SallyTraduction.ps1 -Fichier "C:\docs\manuel.pdf"` |
| Traduire plusieurs fichiers | `.\SallyTraduction.ps1 -Fichier "C:\docs\a.pdf","C:\docs\b.docx"` |
| Traduire tout un dossier (PDF et DOCX) | `.\SallyTraduction.ps1 -Fichier "C:\docs\a_traduire"` |
| Forcer le sens | `-Sens en-fr` ou `-Sens fr-en` (défaut : `auto`) |
| Choisir le dossier de sortie | `-Sortie "C:\docs\traductions"` (défaut : `Documents\SallyTraduction`) |
| Aller ~2× plus vite (sans deuxième avis M2M-100) | `-Rapide` |
| Exécutable ailleurs (clé USB, partage) | `-Exe "E:\SallyTraduction-Portable.exe"` |
| Ouvrir l'interface avec un fichier chargé | `.\SallyTraduction.ps1 -Fichier "C:\docs\manuel.pdf" -Interface` |
| Tout supprimer de l'ordinateur (glossaire conservé) | `.\SallyTraduction.ps1 -Nettoyer` |
| Aide complète | `Get-Help .\SallyTraduction.ps1 -Full` |

La progression s'affiche dans PowerShell, étape par étape. Pour chaque fichier, trois résultats sont créés : `*_FR.pdf` (ou `.docx`), `*_FR_rapport.html` et `*_FR_verification.json`. Ce dernier se rouvre dans l'interface (**Reprendre une vérification…**) pour la relecture page / ligne / mot.
Code de sortie : `0` si tout est traduit, `1` en cas d'erreur, ce qui permet d'automatiser des lots dans un script ou une tâche planifiée.

Appel direct de l'exécutable, sans le script : `Start-Process .\SallyTraduction-Portable.exe -ArgumentList '--cli "C:\docs\manuel.pdf" --dir auto' -Wait`.

Application Windows qui traduit des documents **PDF et Word (.docx)** entre l'anglais et le français, **100 % hors ligne**. Le fichier produit garde le même format et la même mise en page, et un rapport de contrôle qualité l'accompagne. Un écran de **vérification manuelle** donne pour chaque phrase douteuse sa **page, sa ligne et la position du mot**.

📖 **Mode d'emploi détaillé : [GUIDE_UTILISATION.md](GUIDE_UTILISATION.md)**
📦 **Téléchargements (portable et installateur) : page Releases du dépôt**
📊 Banc d'essai des modèles (Opus-MT, Hunyuan-MT-7B, Qwen3-30B-A3B) : [benchmark/](benchmark/README.md)

## Structure du dépôt
| Dossier | Contenu |
|---|---|
| `src/sally_traduction/` | Application : interface (`app.py`, `review.py`), chaîne de traitement (`pipeline.py`), moteurs (`engines.py`), PDF et Word (`documents.py`), localisation (`locate.py`), protection et glossaire (`protect.py`), rapport (`report.py`) |
| `build/` | Construction de l'exécutable (PyInstaller) et des icônes |
| `installer/` | Script Inno Setup de l'installateur |
| `portable/` | Lanceur C# de la version portable en un seul `.exe` |
| `scripts/SallyTraduction.ps1` | Utilisation en ligne de commande PowerShell, sans installation ni droits administrateur |
| `scripts/setup_models.py` | Téléchargement et conversion des modèles dans `models/` (`--dest` pour un autre dossier) |
| `benchmark/` | Banc d'essai des 3 modèles et document de test de 500 pages |
| `tests/` | Petits documents de test et scripts de capture d'interface |

## Construire depuis les sources
Voir le **[Parcours B](#parcours-b--reconstruire-depuis-les-sources)** ci-dessus : toutes les commandes, de `git clone` à l'installateur.

## Installation
Lancer **[SallyTraduction-Setup.exe](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Setup.exe)** (ou `installer\Output\SallyTraduction-Setup-<version>.exe` après construction). Aucun droit administrateur n'est requis par défaut.
Options proposées : icône sur le Bureau, entrée « Traduire avec SallyTraduction » dans le clic droit des PDF et Word.

## Version portable (sans installation, sans droits administrateur)
`portable\Output\SallyTraduction.exe` (≈ 730 Mo) : un seul fichier, à copier où l'on veut (clé USB comprise).
- Premier lancement : décompression unique (~30 s) dans `%LOCALAPPDATA%\SallyTraduction\app-<version>` ; si ce dossier est bloqué, `%TEMP%`, puis un dossier à côté du `.exe`.
- Lancements suivants : immédiats.
- Rien dans le registre ni dans Program Files ; manifeste `asInvoker` (jamais d'élévation demandée).
- Pour tout supprimer : effacer le `.exe` et le dossier `%LOCALAPPDATA%\SallyTraduction`.
- Reconstruire : `powershell -ExecutionPolicy Bypass -File portable\build_portable.ps1` (après `build\build.ps1 -SkipInstaller`).

## Fonctionnement
1. **Analyse** : extraction des blocs de texte. Les blocs de code (police à chasse fixe) sont laissés tels quels.
2. **Traduction** : Opus-MT (CTranslate2 int8). Commandes, chemins, options, identifiants et termes du glossaire sont protégés.
3. **Vérifications** :
   | Contrôle | Outil |
   |---|---|
   | Couverture, langue cible, nombres, éléments techniques | règles + fastText LID |
   | Similarité sémantique source / traduction | MiniLM multilingue (ONNX int8) |
   | Retraduction vers la langue d'origine | Opus-MT inverse + MiniLM |
   | Deuxième avis | M2M-100 418M + MiniLM |
4. **Reconstruction** : même format que l'original (PDF : texte remplacé en place ; Word : styles, tableaux, en-têtes, pieds de page et notes conservés).
5. **Rapport HTML** : score, phrases signalées avec motif, emplacement, retraduction et deuxième avis.
6. **Vérification manuelle** : fiche par phrase signalée avec page, ligne et mot (PDF) ou partie, paragraphe et mot (Word), ouverture du PDF à la bonne page, notes, case « Vérifiée », export CSV ; progression enregistrée dans `*_verification.json`.

## Glossaire
`%APPDATA%\SallyTraduction\glossaire.txt`, une ligne par entrée : `terme anglais = terme français`.
Exemple : `node pool = pool de nœuds` ; pour garder un terme tel quel : `pod = pod`.

## Ligne de commande
```
SallyTraduction.exe --cli document.pdf [autres fichiers…] [--dir auto|en-fr|fr-en] [--out dossier] [--fast]
```

## Limites connues
- Les PDF scannés (images) ne sont pas traduits : il faut d'abord une reconnaissance de texte (OCR).
- Word : la mise en forme *à l'intérieur* d'un paragraphe (un mot en gras au milieu d'une phrase) n'est pas conservée ; le style du paragraphe l'est.
- PDF : le français étant ~15 % plus long, la police est légèrement réduite quand la place manque.
- Le rapport signale les phrases douteuses mais ne remplace pas une relecture humaine pour un livrable client.

## Reconstruire
```
powershell -ExecutionPolicy Bypass -File build\build.ps1
```
Prérequis : `.venv` (voir les dépendances dans `build\build.ps1`), Inno Setup 6, modèles dans `models\`.

## Licence
SallyTraduction est distribué sous licence **GNU AGPL-3.0** (voir [LICENSE](LICENSE)), compatible avec PyMuPDF (AGPL). Les modèles et bibliothèques tiers gardent leurs licences : voir [models/LICENCES-TIERS.txt](models/LICENCES-TIERS.txt).
