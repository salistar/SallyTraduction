# Qwen3-30B-A3B-Instruct-2507

## ⏱ Temps estimé pour le document de test (500 pages) : **≈ 3 h 30 à 4 h 30**

| Élément | Valeur |
|---|---|
| Qualité de traduction | Très bonne (niveau professionnel, relecture légère) |
| Type | LLM généraliste MoE : 30 milliards de paramètres, ~3 milliards actifs par token |
| Licence | Apache 2.0 (usage commercial autorisé) |
| Taille sur disque (Q4_K_M) | ≈ 17-18 Go |
| RAM nécessaire | ≈ 20 Go libres (PC : 31 Go) |
| Vitesse estimée sur ton PC | ≈ 20-30 tokens/s (iGPU Arc 140T, DDR5-5600) |

## Détail du calcul
- Document de test : ≈ 204 000 mots anglais ≈ 276 000 tokens en entrée.
- Texte français produit : ≈ 330 000 tokens (le français est ~20 % plus long).
- Génération : 330 000 / 25 tokens/s ≈ 3 h 40.
- Lecture du texte source par le modèle : + 15 à 30 min.
- Extraction / reconstruction du PDF (pdf2zh / BabelDOC) : + 5 à 10 min.

## À respecter
- Utiliser la version **Instruct-2507**, sans mode « réflexion » (sinon le temps double).
- Fermer les applications lourdes pendant la traduction (le modèle occupe ~17 Go).
- Lancer le soir, récupérer le résultat le matin.

## Mise en place prévue (pas encore installée)
- Moteur : Ollama ou LM Studio (backend Vulkan / IPEX-LLM pour l'Arc 140T).
- Modèle : fichier GGUF Q4_K_M de `Qwen3-30B-A3B-Instruct-2507` (Hugging Face, ex. dépôt `unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF` : nom exact à vérifier au moment de l'installation).
- Outil PDF : `pdf2zh` (PDFMathTranslate) branché sur Ollama.

> Estimation théorique : à confirmer par un test chronométré sur 20 pages.
