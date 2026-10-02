"""Télécharge et convertit les modèles dans models/ (à lancer une fois après le clonage du dépôt).

Prérequis (environnement de construction, pas l'application finale) :
    pip install ctranslate2 transformers sentencepiece torch huggingface_hub
"""
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "models"


def ct2(model, out, extra):
    if (M / out / "model.bin").exists():
        print("déjà présent :", out)
        return
    print("conversion :", model, "->", out, flush=True)
    from ctranslate2.converters import TransformersConverter
    TransformersConverter(model, copy_files=extra, low_cpu_mem_usage=True).convert(
        str(M / out), quantization="int8", force=True)


def main():
    global M
    if "--dest" in sys.argv:                      # dossier de destination (défaut : models/ du dépôt)
        M = Path(sys.argv[sys.argv.index("--dest") + 1]).resolve()
    M.mkdir(parents=True, exist_ok=True)
    ct2("Helsinki-NLP/opus-mt-en-fr", "opus-mt-en-fr-ct2", ["source.spm", "target.spm"])
    ct2("Helsinki-NLP/opus-mt-fr-en", "opus-mt-fr-en-ct2", ["source.spm", "target.spm"])
    ct2("facebook/m2m100_418M", "m2m100_418m-ct2", ["sentencepiece.bpe.model"])
    mini = M / "minilm"
    mini.mkdir(exist_ok=True)
    for f in ("onnx/model_quint8_avx2.onnx", "tokenizer.json", "config.json"):
        dst = mini / Path(f).name
        if not dst.exists():
            shutil.copy(hf_hub_download("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", f), dst)
    lid = M / "lid" / "lid.176.ftz"
    lid.parent.mkdir(exist_ok=True)
    if not lid.exists():
        urllib.request.urlretrieve("https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz", lid)
    print("modèles prêts dans", M)


if __name__ == "__main__":
    main()
