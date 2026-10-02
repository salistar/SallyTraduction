# SallyTraduction 1.1 : traduction technique locale FR ↔ EN

## ⬇️ Téléchargements (dernière version)

| | Lien de téléchargement direct | Taille |
|---|---|---|
| 💼 **Exécutable portable** (sans installation, sans droits administrateur) | **[SallyTraduction-Portable.exe](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Portable.exe)** | **730 Mo** |
| 🧩 **Installateur Windows** (raccourcis, menu Démarrer, clic droit) | **[SallyTraduction-Setup.exe](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Setup.exe)** | **693 Mo** |
| ⌨️ **Script PowerShell** (traduire en ligne de commande, sans installation) | **[SallyTraduction.ps1](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction.ps1)** | 9 Ko |
| 🐍 **Python hors ligne tout-en-un** : modèles utilisés **directement**, sans aucun `.exe` SallyTraduction, sans installation | **[SallyTraduction-Python-Offline.zip](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Python-Offline.zip)** | **742 Mo** |
| 🧠 **Modèles seuls**, déjà convertis (pour `git clone` + Python) | **[SallyTraduction-Models.zip](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Models.zip)** | **635 Mo** |

**Exécutable portable :** `https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Portable.exe`

**Installateur :** `https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Setup.exe`

> **Fonctionne sans internet et sans Ollama** : téléchargez le fichier une fois, puis copiez-le (clé USB) sur l'ordinateur hors ligne. Tous les modèles sont inclus.
> Ces liens pointent toujours vers la dernière version. Empreintes SHA-256 : [SHA256SUMS.txt](https://github.com/salistar/SallyTraduction/releases/latest/download/SHA256SUMS.txt).

## 🚀 Tout depuis `git clone`, commande par commande

Toutes les commandes se tapent dans **PowerShell**, ouvert normalement (menu Démarrer → « PowerShell », **sans** « Exécuter en tant qu'administrateur »). Aucune n'exige de droits administrateur.

| Je veux… | Parcours |
|---|---|
| Utiliser l'application avec l'exécutable portable | **A** |
| **Utiliser directement les modèles avec Python, sans aucun `.exe`** (avec ou sans internet) | **C** |
| Tout reconstruire depuis les sources (exécutable, portable, installateur) | **B** |

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

### Parcours C : utiliser **directement les modèles** avec Python (aucun `.exe` SallyTraduction)

Les modèles (Opus-MT, M2M-100, MiniLM, fastText) tournent directement dans Python : pas d'exécutable SallyTraduction, pas d'Ollama, pas de connexion pendant la traduction, aucun droit administrateur.

#### C1. Ordinateur **avec** internet, depuis `git clone`

**Prérequis :** Python **3.11, 3.12, 3.13 ou 3.14** (64 bits), installé pour l'utilisateur courant, sans droits administrateur : `winget install Python.Python.3.13 --scope user`, ou l'installateur de python.org avec « Install for me only ». Vérifiez la version avec `python --version`.

```powershell
# 1. Récupérer le projet
git clone https://github.com/salistar/SallyTraduction.git

# 2. Entrer dans le dossier
cd SallyTraduction

# 3. Créer l'environnement Python du projet
python -m venv .venv

# 4. Mettre pip à jour
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# 5. Installer uniquement ce qu'il faut pour traduire (ni PyInstaller, ni PyTorch)
.\.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt

# 6. Télécharger les modèles déjà convertis dans models\ (635 Mo, empreinte SHA-256 vérifiée)
.\.venv\Scripts\python.exe scripts\setup_models.py --prebuilt

# 7. Traduire une phrase (sens détecté automatiquement)
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Texte "The on-call engineer must approve the change."

# 8. Traduire le document de test, puis vos documents (un fichier, plusieurs, ou un dossier)
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier tests\Helios_Guide_EN.docx
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier "C:\docs\manuel.pdf"
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier "C:\docs\a_traduire" -Sens en-fr -Sortie "C:\docs\traductions" -Rapide

# 9. Ouvrir l'interface graphique (vérification manuelle page / ligne / mot comprise)
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1

# 10. Utiliser les modèles dans vos propres scripts Python (exemple commenté)
.\.venv\Scripts\python.exe examples\utiliser_les_modeles.py
```

Même chose sans le script `Traduire.ps1`, en appelant Python directement :
```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m sally_traduction --texte "Restart the replicas one at a time." --dir en-fr
.\.venv\Scripts\python.exe -m sally_traduction --cli "C:\docs\manuel.pdf" "C:\docs\guide.docx" --dir auto --out "C:\docs\traductions"
.\.venv\Scripts\python.exe -m sally_traduction
```

#### C2. Ordinateur **sans** internet : zip Python tout-en-un

Le zip contient un Python 3.11 **embarqué**, c'est-à-dire la distribution officielle « embeddable » de python.org, qui ne s'installe pas. Il contient aussi les bibliothèques, l'interface (Tcl/Tk), les 5 modèles, le code source, les scripts et les exemples. Il suffit de le décompresser.

```powershell
# Sur un PC connecté : télécharger le zip (742 Mo), puis le copier sur une clé USB
curl.exe -L -o SallyTraduction-Python-Offline.zip https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Python-Offline.zip
```
```powershell
# Sur le PC hors ligne :
# 1. Décompresser dans votre dossier personnel (≈ 1 Go)
Expand-Archive E:\SallyTraduction-Python-Offline.zip -DestinationPath $HOME\SallyTraduction-Offline

# 2. Entrer dans le dossier
cd $HOME\SallyTraduction-Offline\SallyTraduction

# 3. Traduire une phrase
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Texte "Always create a snapshot before deleting the volume."

# 4. Traduire des documents
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier tests
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier "C:\docs\manuel.pdf"

# 5. Ouvrir l'interface graphique
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1

# 6. Utiliser les modèles dans vos scripts Python
.\runtime\python.exe examples\utiliser_les_modeles.py
```
Scripts interdits par l'entreprise : `& ([scriptblock]::Create((Get-Content .\scripts\Traduire.ps1 -Raw))) -Fichier "C:\docs\manuel.pdf"`.
Vérifié : traduction complète avec **0 tentative de connexion réseau**.

Pour **fabriquer ce zip vous-même** à partir du clone (Python 3.11 installé, modèles présents dans `models\`) :
```powershell
powershell -ExecutionPolicy Bypass -File scripts\make_offline_bundle.ps1
# résultat : dist-offline\SallyTraduction-Python-Offline.zip
```

#### C3. Utiliser les modèles dans votre propre code Python
```python
import sys; sys.path.insert(0, "src")
from sally_traduction import engines, protect

glossaire = protect.load_glossary("en-fr")                      # %APPDATA%\SallyTraduction\glossaire.txt
masque, valeurs = protect.protect("Run kubectl get pods before draining the node pool.", glossaire)
brut = engines.OpusTranslator("opus-en-fr").translate([masque])[0]
print(protect.restore(brut, valeurs, "fr")[0])
# -> Exécutez kubectl get pods avant de vider le pool de nœuds.

from sally_traduction.pipeline import run, Options              # chaîne complète sur un document
r = run("C:/docs/manuel.pdf", "C:/docs/traductions", Options(direction="auto"))
print(r.output, r.report, r.review, r.flagged, r.sentences)
```
Exemple complet et commenté : [examples/utiliser_les_modeles.py](examples/utiliser_les_modeles.py). Il utilise aussi CTranslate2 seul, la détection de langue et la similarité de sens.

### Parcours B : reconstruire depuis les sources

**Prérequis, tous installables sans droits administrateur :**
| Outil | Installation pour l'utilisateur courant |
|---|---|
| Git | `winget install Git.Git --scope user`, ou [Git portable](https://git-scm.com/download/win) |
| Python **3.11, 3.12, 3.13 ou 3.14** (64 bits) | `winget install Python.Python.3.13 --scope user`, ou l'installateur de python.org avec « Install for me only » |
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
#    La dernière ligne doit commencer par « Successfully installed ». Sinon, voir « Dépannage » ci-dessous.
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 6. Installer les outils de conversion des modèles (≈ 300 Mo, utilisés seulement à l'étape 7)
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install transformers huggingface_hub

# 7. Préparer les 5 modèles dans models\
#    Convertit les originaux depuis huggingface.co (≈ 3 Go la première fois). Si huggingface.co est bloqué
#    (réseau d'entreprise), le script bascule seul sur les modèles déjà convertis publiés sur GitHub (635 Mo).
.\.venv\Scripts\python.exe scripts\setup_models.py
#    Directement depuis GitHub, sans les étapes 6 et 7 :
#    .\.venv\Scripts\python.exe scripts\setup_models.py --prebuilt
#    Sans aucune connexion, avec un SallyTraduction-Models.zip téléchargé au navigateur ou copié par clé USB :
#    .\.venv\Scripts\python.exe scripts\setup_models.py --zip "C:\Users\moi\Downloads\SallyTraduction-Models.zip"

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

### Dépannage

| Symptôme | Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'ctranslate2'` à l'étape 7 | L'étape 5 a échoué : pip installe tout ou rien, donc un seul paquet en échec bloque toute la liste. Avant la version 1.1.1, `fasttext-wheel` n'avait pas de paquet pour Python 3.13+ | `git pull`, puis relancer l'étape 5 (fastText est désormais facultatif sous Python 3.13+) |
| `OSError: We couldn't connect to 'https://huggingface.co'` ou `LocalEntryNotFoundError` à l'étape 7 | huggingface.co est bloqué par le pare-feu ou le proxy de l'entreprise (GitHub, lui, passe) | `git pull` puis relancer l'étape 7 : le script bascule seul sur les modèles convertis de GitHub. Ou directement `setup_models.py --prebuilt` |
| Même GitHub est bloqué pour Python à l'étape 7 | Proxy ou inspection SSL de l'entreprise | Le script réessaie avec `curl.exe`. Sinon, téléchargez **[SallyTraduction-Models.zip](https://github.com/salistar/SallyTraduction/releases/latest/download/SallyTraduction-Models.zip)** avec le navigateur, puis `setup_models.py --zip "<chemin du zip>"` |
| `error: Microsoft Visual C++ 14.0 or greater is required` pendant l'étape 5 | Un paquet n'a pas de version précompilée pour votre Python et pip tente de le compiler | `git pull` (dépendances corrigées) ; sinon utilisez Python 3.12 ou 3.13 |
| `python` ouvre le Microsoft Store ou n'existe pas | Python n'est pas installé ou pas dans le PATH | `winget install Python.Python.3.13 --scope user`, puis fermez et rouvrez PowerShell |
| `python --version` n'affiche pas la version voulue | Plusieurs Python installés | Remplacez l'étape 3 par `py -3.13 -m venv .venv` (ou `-3.12`, `-3.11`) |
| Les scripts `.ps1` sont refusés (« l'exécution de scripts est désactivée ») | Stratégie d'exécution | Gardez `powershell -ExecutionPolicy Bypass -File …` comme dans les commandes, ou la forme `& ([scriptblock]::Create((Get-Content … -Raw)))` |
| Repartir de zéro | Environnement abîmé | Supprimez le dossier `.venv` puis reprenez à l'étape 3 |

Sous Python 3.13 et plus, la détection de langue utilise un **détecteur intégré** anglais / français (aussi fiable que fastText sur le document de test : 100 % en français, 99,6 % en anglais). Sous Python 3.11 et 3.12, fastText est utilisé.

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
| `scripts/Traduire.ps1` | **Modèles utilisés directement avec Python** (texte, fichiers, dossiers, interface), sans `.exe` |
| `scripts/SallyTraduction.ps1` | Même usage via l'exécutable portable, sans installation ni droits administrateur |
| `scripts/setup_models.py` | Modèles dans `models/` : `--prebuilt` (déjà convertis, 635 Mo) ou conversion soi-même ; `--dest` pour un autre dossier |
| `scripts/make_offline_bundle.ps1` | Fabrique le zip Python hors ligne tout-en-un |
| `examples/utiliser_les_modeles.py` | Exemple commenté d'utilisation des modèles dans du code Python |
| `requirements-runtime.txt` / `requirements.txt` | Dépendances pour traduire / pour construire les exécutables |
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

---

## 🌸 Plan Sally : modèles depuis la Release, fichier à traduire sur le Bureau

Le plus simple pour traduire un document posé sur votre **Bureau**, avec les modèles utilisés **directement par Python**. Aucun `.exe` SallyTraduction, aucun droit administrateur, aucune connexion à huggingface.co : les modèles viennent de la **Release GitHub**.

**Prérequis :** Python 3.11 à 3.14 (64 bits) installé pour l'utilisateur courant (`winget install Python.Python.3.13 --scope user`) et Git (ou le zip du dépôt, voir le parcours A, étape 1 bis).

### Une seule fois : installation

```powershell
# 1. Se placer dans son dossier personnel
cd $HOME

# 2. Récupérer le projet
git clone https://github.com/salistar/SallyTraduction.git

# 3. Entrer dans le dossier
cd SallyTraduction

# 4. Créer l'environnement Python
python -m venv .venv

# 5. Mettre pip à jour
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# 6. Installer ce qu'il faut pour traduire (dernière ligne : « Successfully installed … »)
.\.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt

# 7. Télécharger les modèles depuis la Release GitHub (635 Mo, empreinte SHA-256 vérifiée)
.\.venv\Scripts\python.exe scripts\setup_models.py --prebuilt

# 8. Vérifier que tout marche avec une phrase
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Texte "The on-call engineer must approve the change."
```

### À chaque traduction : posez le fichier sur le Bureau, puis

```powershell
# 1. Aller dans le dossier du projet
cd $HOME\SallyTraduction

# 2. Repérer le Bureau (fonctionne aussi quand il est redirigé vers OneDrive)
$Bureau = [Environment]::GetFolderPath("Desktop")

# 3. Voir les documents présents sur le Bureau
Get-ChildItem "$Bureau\*" -Include *.pdf, *.docx -Name

# 4. Traduire VOTRE fichier : remplacez mon_document.pdf par son nom exact (PDF ou .docx)
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier "$Bureau\mon_document.pdf" -Sortie "$Bureau\Traductions"

# 5. Ouvrir le dossier des résultats sur le Bureau
explorer "$Bureau\Traductions"
```

Dans `Bureau\Traductions`, vous trouvez pour chaque document :

| Fichier | Contenu |
|---|---|
| `mon_document_FR.pdf` (ou `_EN`, ou `.docx`) | Le document traduit, au même format |
| `mon_document_FR_rapport.html` | Le rapport de contrôle qualité (double-clic pour l'ouvrir) |
| `mon_document_FR_verification.json` | Les phrases à relire, avec **page, ligne et mot** |

### Variantes utiles

```powershell
# Traduire TOUS les PDF et Word posés sur le Bureau, en une fois
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier $Bureau -Sortie "$Bureau\Traductions"

# Forcer le sens : français vers anglais
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier "$Bureau\mon_document.pdf" -Sens fr-en -Sortie "$Bureau\Traductions"

# Deux fois plus rapide (sans le deuxième avis M2M-100), pour un premier jet
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1 -Fichier "$Bureau\mon_document.pdf" -Rapide -Sortie "$Bureau\Traductions"

# Relire les phrases signalées page / ligne / mot dans l'interface :
# « Reprendre une vérification… » puis choisir Bureau\Traductions\mon_document_FR_verification.json
powershell -ExecutionPolicy Bypass -File scripts\Traduire.ps1

# Mettre à jour le projet plus tard (les modèles déjà téléchargés sont conservés)
cd $HOME\SallyTraduction
git pull
.\.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt
```

> **Astuce :** le nom du fichier contient des espaces ou des accents ? Gardez les guillemets : `-Fichier "$Bureau\Rapport annuel 2026.pdf"`.
> **Pas d'internet sur ce PC ?** Remplacez l'étape 7 de l'installation par `.\.venv\Scripts\python.exe scripts\setup_models.py --zip "E:\SallyTraduction-Models.zip"`, après avoir copié le zip des modèles sur une clé USB.
