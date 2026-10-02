# Opus-MT fr-en / en-fr (Helsinki-NLP), accéléré avec CTranslate2 int8 ou OpenVINO

## ⏱ Temps estimé pour le document de test (500 pages) : **≈ 10 à 20 min**

| Élément | Valeur |
|---|---|
| Qualité de traduction | Correcte, sans plus : phrases parfois raides, termes techniques à relire |
| Type | Modèle de traduction neuronale spécialisé (Marian), ≈ 75 millions de paramètres par sens |
| Licence | CC-BY 4.0 (usage commercial autorisé, avec attribution) |
| Taille sur disque (int8) | ≈ 80 Mo par sens de traduction |
| RAM nécessaire | < 2 Go |
| Vitesse estimée sur ton PC | Plusieurs centaines à quelques milliers de tokens/s (traitement par lots sur les 16 cœurs du Core Ultra 7 255H) |

## Détail du calcul
- Document de test : ≈ 204 000 mots ≈ 276 000 tokens.
- Traduction : ≈ 3 à 8 min avec CTranslate2 int8 en lots de 32 phrases.
- Extraction / reconstruction du PDF : ≈ 5 à 10 min. C'est l'étape la plus longue ici.

## Modèles utilisés
- Anglais → français : `Helsinki-NLP/opus-mt-en-fr`
- Français → anglais : `Helsinki-NLP/opus-mt-fr-en`

## Mise en place prévue (pas encore installée)
```bash
pip install ctranslate2 transformers sentencepiece
ct2-transformers-converter --model Helsinki-NLP/opus-mt-en-fr --output_dir opus-mt-en-fr-ct2 --quantization int8
ct2-transformers-converter --model Helsinki-NLP/opus-mt-fr-en --output_dir opus-mt-fr-en-ct2 --quantization int8
```
Variante OpenVINO : export via `optimum-intel` pour utiliser l'iGPU Arc 140T. C'est à tester : sur ce petit modèle, le processeur seul est souvent aussi rapide.

## Quand l'utiliser
- Premier jet rapide, ou besoin d'un résultat en moins de 15 minutes.
- Pas pour un livrable client sans relecture humaine.

> Estimation théorique : à confirmer par un test chronométré sur 20 pages.
