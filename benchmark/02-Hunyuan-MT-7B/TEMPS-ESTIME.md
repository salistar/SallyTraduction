# Hunyuan-MT-7B (Tencent)

## ⏱ Temps estimé pour le document de test (500 pages) : **≈ 6 h à 8 h**

| Élément | Valeur |
|---|---|
| Qualité de traduction | Excellente : modèle spécialisé en traduction, classé premier sur la plupart des paires de langues au WMT25 |
| Type | LLM dense de 7 milliards de paramètres, dédié à la traduction |
| Licence | Licence Tencent Hunyuan (restrictive : à relire avant un usage client) |
| Taille sur disque (Q4_K_M) | ≈ 4,5-5 Go |
| RAM nécessaire | ≈ 8 Go libres |
| Vitesse estimée sur ton PC | ≈ 12-15 tokens/s (iGPU Arc 140T, DDR5-5600) |

## Détail du calcul
- Document de test : ≈ 204 000 mots anglais ≈ 276 000 tokens en entrée.
- Texte français produit : ≈ 330 000 tokens.
- Génération : 330 000 / 13,5 tokens/s ≈ 6 h 50.
- Lecture du texte source + extraction et reconstruction du PDF : + 20 à 40 min.

## Pourquoi il est plus lent que Qwen3-30B-A3B alors qu'il est plus petit
Il est « dense » : ses 7 milliards de paramètres travaillent à chaque token, contre environ 3 milliards pour Qwen3-30B-A3B. Sur un iGPU, la vitesse dépend surtout de la quantité de données lue en RAM par token.

## Atout
Il consomme peu de mémoire : le PC reste utilisable pendant la traduction.

## Mise en place prévue (pas encore installée)
- Moteur : Ollama ou LM Studio (Vulkan / IPEX-LLM).
- Modèle : `tencent/Hunyuan-MT-7B` en GGUF Q4_K_M (dépôt GGUF exact à vérifier au moment de l'installation).
- Respecter le format de prompt de traduction recommandé par Tencent.

> Estimation théorique : à confirmer par un test chronométré sur 20 pages.
