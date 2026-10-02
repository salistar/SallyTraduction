# sallyTraduction : traduction locale FR ↔ EN de documents techniques

PC de test : Intel Core Ultra 7 255H (16 cœurs), 31 Go de RAM DDR5-5600, iGPU Intel Arc 140T, sans carte graphique dédiée.

## Comparatif sur le document de test (500 pages, ≈ 204 000 mots)

| Dossier | Modèle | Temps estimé | Qualité | Licence |
|---|---|---|---|---|
| `01-Qwen3-30B-A3B-Instruct-2507` | Qwen3-30B-A3B-Instruct-2507 | **≈ 3 h 30 à 4 h 30** | Très bonne | Apache 2.0 |
| `02-Hunyuan-MT-7B` | Hunyuan-MT-7B | **≈ 6 h à 8 h** | Excellente | Tencent (restrictive) |
| `03-Opus-MT-CTranslate2-OpenVINO` | Opus-MT en-fr / fr-en | **≈ 10 à 20 min** | Correcte | CC-BY 4.0 |

Ces temps sont des estimations théoriques.

## Résultats mesurés le 02/10/2026 (pages 11 à 30, 8 601 mots, anglais → français)

| Modèle | Durée pour 20 pages | Projection 500 pages | Vitesse | Qualité observée |
|---|---|---|---|---|
| Opus-MT (CTranslate2 int8, processeur) | 8 s | **≈ 3 min 20 s** | ≈ 1 750 tokens/s | Correcte, littérale ; contresens sur le jargon (« avion de contrôle ») |
| Hunyuan-MT-7B (Q4_K_M, iGPU Vulkan) | 32 min 44 s | ≈ 13 h | 10,5 tokens/s | Fluide mais peu fidèle : contresens, ajouts inventés, commentaires parasites |
| Qwen3-30B-A3B (UD-Q3_K_XL, iGPU Vulkan) | 1 h 25 min* | ≈ 34 h* | 3,6 tokens/s | **La plus fidèle** : terminologie juste, structure respectée |

\* Mesure dégradée : la RAM était saturée (14 Go pour le modèle) et d'autres travaux tournaient en parallèle.

Traductions complètes et mesures détaillées : dossier `outputs`.

**Conclusion :** sur ce PC (iGPU Arc 140T, 31 Go de RAM), seul Opus-MT est utilisable pour 500 pages. Il a servi de base à l'application `Desktop\SallyTraductionApp`, qui ajoute protection des termes, glossaire et contrôles qualité.

## Document de test
`00-Document-Test/Helios_Operations_Manual_EN_500p.pdf` est un manuel d'exploitation fictif en anglais :
- 500 pages : couverture, sommaire de 9 pages, 46 chapitres, 359 sections ;
- paragraphes, listes, procédures numérotées, tableaux, blocs de code (YAML, Bash, Terraform, SQL, NGINX, Rego…), notes et avertissements ;
- signets PDF par chapitre.

Pour le régénérer (Python 3 standard, aucune dépendance) :
```bash
python 00-Document-Test/generate_test_pdf.py
```
Options : `--pages 500`, `--seed 42` (même document à chaque fois), `--out fichier.pdf`.
