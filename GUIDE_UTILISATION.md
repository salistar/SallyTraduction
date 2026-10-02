# Guide d'utilisation : SallyTraduction 1.1

SallyTraduction traduit vos documents **PDF et Word (.docx)** de l'anglais vers le français et inversement, **sans connexion internet** : vos fichiers ne quittent jamais l'ordinateur. Le document traduit garde le format et la mise en page d'origine, et l'application signale les phrases à vérifier en indiquant **la page, la ligne et le mot** où elles se trouvent.

---

## 1. Choisir sa version

| Version | Fichier | Quand l'utiliser |
|---|---|---|
| **Portable** | `SallyTraduction.exe` (≈ 730 Mo) | Pas de droits administrateur, PC professionnel, clé USB, aucune installation souhaitée |
| **Installateur** | `SallyTraduction-Setup-1.1.0.exe` (≈ 690 Mo) | PC personnel : raccourcis, menu Démarrer, clic droit « Traduire avec SallyTraduction » |

Les deux se téléchargent dans la page **Releases** du dépôt GitHub. Configuration requise : Windows 10 ou 11 en 64 bits, 8 Go de RAM au minimum (16 Go conseillés), 2 Go d'espace libre et un processeur avec AVX2 (tous les PC depuis 2015 environ).

---

## 2. Lancer l'application

### Version portable (sans installation, sans droits administrateur)
1. Copiez `SallyTraduction.exe` où vous voulez : Bureau, dossier personnel ou clé USB.
2. Double-cliquez dessus.
3. **Premier lancement uniquement** : une fenêtre « Préparation du premier lancement » s'affiche pendant environ 30 secondes, le temps de décompresser l'application dans `%LOCALAPPDATA%\SallyTraduction`. Si ce dossier est bloqué, elle utilise le dossier temporaire, puis un dossier à côté du `.exe`.
4. Les lancements suivants sont immédiats.

> Si Windows affiche « Windows a protégé votre ordinateur » (SmartScreen), cliquez sur **Informations complémentaires** puis **Exécuter quand même**. Ce message apparaît pour tout programme sans signature numérique. Si votre entreprise bloque les programmes non approuvés (AppLocker), seul votre service informatique peut autoriser l'application.

### Version installée
Lancez `SallyTraduction-Setup-1.1.0.exe`, suivez l'assistant (aucun droit administrateur requis par défaut), puis ouvrez **SallyTraduction** depuis le menu Démarrer ou le Bureau.
Avec l'option « clic droit » cochée, il suffit de faire un clic droit sur un PDF ou un Word puis **Traduire avec SallyTraduction**.

---

## 3. Traduire un document, pas à pas

1. **Choisir le fichier** : faites-le glisser dans la grande zone « Glissez-déposez votre fichier ici », ou cliquez sur **Parcourir…**. La carte du fichier affiche son nom, son nombre de pages et sa taille.
2. **Sens de traduction** :
   - **Détection auto** (conseillé) : l'application reconnaît la langue du document ;
   - **Anglais → Français** ou **Français → Anglais** pour forcer le sens.
3. **Dossier de sortie** : par défaut `Documents\SallyTraduction`. Cliquez sur **Choisir** pour en changer.
4. **Contrôles qualité** : les trois interrupteurs sont activés par défaut.
   | Contrôle | Ce qu'il vérifie | Coût en temps |
   |---|---|---|
   | Retraduction | Retraduit le résultat vers la langue d'origine et compare le sens | moyen |
   | Similarité sémantique | Mesure la proximité de sens entre chaque phrase et sa traduction | faible |
   | Deuxième avis | Un second traducteur indépendant (M2M-100) signale les désaccords | élevé |
   La langue, les nombres et les éléments techniques sont **toujours** vérifiés. Pour aller plus vite, désactivez le deuxième avis : le temps est divisé par 2 environ.
5. Cliquez sur **Lancer la traduction**. Le suivi montre les 5 étapes (Analyse, Traduction, Vérifications, Reconstruction, Rapport), la barre de progression, le temps écoulé et le temps restant. Le bouton **Annuler** arrête proprement.

**Durée indicative** (processeur récent, 16 cœurs) : environ 40 s pour 20 pages ; 10 à 20 min pour 500 pages avec tous les contrôles.

---

## 4. Résultat

À la fin, une carte affiche :
- **l'anneau de score** : pourcentage de phrases validées automatiquement ;
- **le nombre de phrases à relire**, la couverture, la langue cible, les nombres conservés, la similarité moyenne ;
- les boutons **Vérification manuelle (N)**, **Ouvrir le document traduit**, **Rapport de contrôle** et **Ouvrir le dossier**.

Trois fichiers sont créés dans le dossier de sortie :

| Fichier | Contenu |
|---|---|
| `MonDocument_FR.pdf` ou `.docx` | Le document traduit, au même format que l'original |
| `MonDocument_FR_rapport.html` | Le rapport de contrôle (s'ouvre dans le navigateur, thème clair ou sombre) |
| `MonDocument_FR_verification.json` | Le suivi de la vérification manuelle (repris automatiquement) |

---

## 5. Vérification manuelle (page, ligne, mot)

Cliquez sur **Vérification manuelle (N)**. Chaque phrase signalée apparaît dans une fiche :

- **Emplacement**, par exemple `Page 12 · ligne 18 · mot 5` :
  - *PDF* : page telle que numérotée par le lecteur PDF, ligne comptée **depuis le haut de la page** (en-tête compris), mot compté **depuis le début de la ligne**. Dans un tableau, toutes les cellules d'une même rangée forment une seule ligne, lue de gauche à droite ;
  - *Word* : la pagination dépend de l'affichage de Word, donc l'emplacement indique la **partie** (Corps, En-tête, Pied de page, Notes), le **numéro de paragraphe** (paragraphes non vides) et le **mot** depuis le début du paragraphe.
- **Autres emplacements** : la même phrase peut apparaître plusieurs fois (« aussi : Page 40 · ligne 3 · mot 1 »).
- **Motifs** en couleur : rouge pour un problème certain (non traduite, mauvaise langue, terme perdu), orange pour un doute (sens éloigné, retraduction divergente, désaccord du second traducteur).
- **Original et traduction côte à côte**, chacun avec son emplacement, plus la retraduction et la proposition du second traducteur pour vous aider.

Actions sur chaque fiche :
| Action | Effet |
|---|---|
| **Ouvrir à la page N** (PDF) | Ouvre le PDF traduit directement à la bonne page dans votre navigateur |
| **Copier la traduction** / **Copier l'emplacement** | Copie dans le presse-papiers, pour corriger dans Word ou Acrobat |
| Champ **Note ou correction proposée** | Votre correction ou un commentaire, enregistré automatiquement |
| Case **Vérifiée** | Marque la phrase comme relue ; le compteur « x / N vérifiée(s) » progresse |

En haut de la fenêtre :
- **recherche** dans l'original, la traduction et les notes ;
- **filtre par motif** ;
- **À vérifier / Vérifiées / Toutes** ;
- **Exporter (CSV)** : tableau pour Excel avec numéro, statut, emplacements, motifs, original, traduction et note, à transmettre à un relecteur.

Le travail est **enregistré au fur et à mesure**. Pour le reprendre plus tard, cliquez sur **Reprendre une vérification…** dans la barre latérale et choisissez le fichier `_verification.json`.

---

## 6. Glossaire : imposer vos termes

Fichier : `%APPDATA%\SallyTraduction\glossaire.txt` (créé au premier usage ; tapez `%APPDATA%` dans l'Explorateur).

```
# terme anglais = terme français
node pool = pool de nœuds
on-call engineer = ingénieur d'astreinte
pod = pod                    (garder le terme tel quel)
```
- Une entrée par ligne, sans tenir compte des majuscules ; l'entrée la plus longue est prioritaire.
- Le glossaire sert dans les deux sens (français → anglais : lu de droite à gauche).
- Sont aussi **protégés automatiquement** : commandes (`kubectl get nodes -o wide`), options (`--timeout=300s`), chemins, URL, adresses e-mail, identifiants (`kube_apiserver.batch_size`), noms en CamelCase (`PodDisruptionBudget`), et le code (police à chasse fixe), qui n'est jamais traduit.

---

## 7. Ligne de commande (automatisation)

```
SallyTraduction.exe --cli "C:\docs\manuel.pdf" --dir auto --out "C:\docs\traductions"
SallyTraduction.exe --cli "C:\docs\guide.docx" --dir en-fr --fast
```
`--dir auto|en-fr|fr-en` choisit le sens, `--out` le dossier de sortie, et `--fast` désactive le deuxième avis.

---

## 8. Questions fréquentes

**Le texte traduit est un peu plus petit dans le PDF ?** Le français est environ 15 % plus long que l'anglais. L'application réduit légèrement la police quand la place manque, de façon homogène sur la page.

**Mon PDF n'est pas traduit (« aucun texte trouvé »)** : c'est un PDF scanné, donc une image. Il faut d'abord le passer dans un logiciel de reconnaissance de texte (OCR).

**Un mot en gras au milieu d'une phrase a perdu son gras (Word)** : la mise en forme *à l'intérieur* d'un paragraphe n'est pas conservée. Le style du paragraphe (titre, liste, tableau) l'est.

**Format .doc (Word 97-2003)** : ouvrez-le dans Word et enregistrez-le en `.docx`.

**La traduction est-elle garantie à 100 % ?** Non. Le contrôle garantit que tout est traduit (couverture, langue, nombres, code). Pour le sens, il signale les phrases douteuses : relisez-les avec l'écran de vérification manuelle avant tout livrable client.

**Désinstaller** : version portable, supprimez le `.exe` et le dossier `%LOCALAPPDATA%\SallyTraduction`. Version installée : Paramètres → Applications → SallyTraduction → Désinstaller.
