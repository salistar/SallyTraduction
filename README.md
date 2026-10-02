# SallyTraduction 1.1 : traduction technique locale FR ↔ EN

## ⬇️ Téléchargements (version 1.1.0)

| | Lien de téléchargement direct | Taille |
|---|---|---|
| 💼 **Exécutable portable** (sans installation, sans droits administrateur) | **[SallyTraduction-Portable-1.1.0.exe](https://github.com/salistar/SallyTraduction/releases/download/v1.1.0/SallyTraduction-Portable-1.1.0.exe)** | **730 Mo** |
| 🧩 **Installateur Windows** (raccourcis, menu Démarrer, clic droit) | **[SallyTraduction-Setup-1.1.0.exe](https://github.com/salistar/SallyTraduction/releases/download/v1.1.0/SallyTraduction-Setup-1.1.0.exe)** | **693 Mo** |

**Exécutable portable :** `https://github.com/salistar/SallyTraduction/releases/download/v1.1.0/SallyTraduction-Portable-1.1.0.exe`

**Installateur :** `https://github.com/salistar/SallyTraduction/releases/download/v1.1.0/SallyTraduction-Setup-1.1.0.exe`

> **Fonctionne sans internet et sans Ollama** : téléchargez le fichier une fois, puis copiez-le (clé USB) sur l'ordinateur hors ligne. Tous les modèles sont inclus.

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
| `scripts/setup_models.py` | Téléchargement et conversion des modèles dans `models/` |
| `benchmark/` | Banc d'essai des 3 modèles et document de test de 500 pages |
| `tests/` | Petits documents de test et scripts de capture d'interface |

## Construire depuis les sources
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
pip install torch transformers huggingface_hub     # conversion des modèles seulement
python scripts\setup_models.py
powershell -ExecutionPolicy Bypass -File build\build.ps1              # exécutable + installateur
powershell -ExecutionPolicy Bypass -File portable\build_portable.ps1  # version portable
```

## Installation
Lancer `installer\Output\SallyTraduction-Setup-1.1.0.exe`. Aucun droit administrateur n'est requis par défaut.
Options proposées : icône sur le Bureau, entrée « Traduire avec SallyTraduction » dans le clic droit des PDF et Word.

## Version portable (sans installation, sans droits administrateur)
`portable\Output\SallyTraduction.exe` (≈ 730 Mo) : un seul fichier, à copier où l'on veut (clé USB comprise).
- Premier lancement : décompression unique (~30 s) dans `%LOCALAPPDATA%\SallyTraduction\app-1.1.0` ; si ce dossier est bloqué, `%TEMP%`, puis un dossier à côté du `.exe`.
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
SallyTraduction.exe --cli document.pdf [--dir auto|en-fr|fr-en] [--out dossier] [--fast]
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

## Licences
Voir `models\LICENCES-TIERS.txt`. Attention : PyMuPDF est sous licence AGPL ; une distribution commerciale fermée nécessite une licence Artifex.
