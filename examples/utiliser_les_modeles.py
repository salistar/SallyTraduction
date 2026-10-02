r"""Utiliser directement les modèles de SallyTraduction dans vos propres scripts Python.

Lancement depuis la racine du projet :
    .\.venv\Scripts\python.exe examples\utiliser_les_modeles.py      (après git clone, parcours C)
    .\runtime\python.exe examples\utiliser_les_modeles.py            (zip hors ligne)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# ---------------------------------------------------------------------------
# 1. Le modèle Opus-MT seul, avec CTranslate2 et SentencePiece (aucune dépendance au projet)
# ---------------------------------------------------------------------------
import ctranslate2
import sentencepiece as spm

modele = ROOT / "models" / "opus-mt-en-fr-ct2"
sp_src = spm.SentencePieceProcessor(model_file=str(modele / "source.spm"))
sp_tgt = spm.SentencePieceProcessor(model_file=str(modele / "target.spm"))
traducteur = ctranslate2.Translator(str(modele), device="cpu", compute_type="int8")

phrases = ["The backup is encrypted before it leaves the data centre.",
           "Restart the replicas one at a time to avoid an outage."]
lots = [sp_src.encode(p, out_type=str) + ["</s>"] for p in phrases]
for p, r in zip(phrases, traducteur.translate_batch(lots, beam_size=2)):
    print("EN :", p)
    print("FR :", sp_tgt.decode([t for t in r.hypotheses[0] if t != "</s>"]))

# ---------------------------------------------------------------------------
# 2. Les moteurs du projet : protection des termes techniques et glossaire compris
# ---------------------------------------------------------------------------
from sally_traduction import engines, protect

glossaire = protect.load_glossary("en-fr")
texte = "Run kubectl get pods before draining the node pool."
masque, valeurs = protect.protect(texte, glossaire)
brut = engines.OpusTranslator("opus-en-fr").translate([masque])[0]
print("\nAvec protection :", protect.restore(brut, valeurs, "fr")[0])

# Détection de langue et similarité de sens entre l'original et la traduction
print("Langue détectée :", engines.LangID().detect(["Le plan de contrôle est indisponible."])[0])
emb = engines.Embedder()
a, b = emb.encode(["The control plane is unavailable.", "Le plan de contrôle est indisponible."])
print("Similarité EN/FR : %.2f" % float(a @ b))

# ---------------------------------------------------------------------------
# 3. La chaîne complète sur un document (même résultat que l'application)
# ---------------------------------------------------------------------------
from sally_traduction.pipeline import Options, run

resultat = run(ROOT / "tests" / "Helios_Guide_EN.docx", Path.home() / "Documents" / "SallyTraduction",
               Options(direction="en-fr", second_opinion=False))
print("\nDocument traduit :", resultat.output)
print("Phrases à relire  : %d sur %d" % (resultat.flagged, resultat.sentences))
