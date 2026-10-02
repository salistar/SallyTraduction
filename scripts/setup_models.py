"""Prépare les modèles dans models/ (à lancer une fois après le clonage du dépôt).

    python scripts/setup_models.py --prebuilt   # modèles déjà convertis (≈ 650 Mo), sans PyTorch : recommandé
    python scripts/setup_models.py              # télécharge les originaux et les convertit soi-même
    option --dest DOSSIER                       # autre dossier que models/

La conversion soi-même demande : pip install ctranslate2 transformers sentencepiece torch huggingface_hub
"""
import hashlib
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

RELEASE = "https://github.com/salistar/SallyTraduction/releases/latest/download/"
MODELS_ZIP = "SallyTraduction-Models.zip"

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


def prebuilt():
    """Télécharge le zip des modèles convertis depuis la dernière Release et vérifie son empreinte SHA-256."""
    zp = M / MODELS_ZIP
    print("téléchargement de", MODELS_ZIP, "(≈ 650 Mo)…", flush=True)

    def hook(n, bs, total):
        if total > 0 and n % 400 == 0:
            print("  %3d %%" % min(100, n * bs * 100 // total), flush=True)
    urllib.request.urlretrieve(RELEASE + MODELS_ZIP, zp, hook)
    sums = urllib.request.urlopen(RELEASE + "SHA256SUMS.txt").read().decode()
    want = next((l.split()[0] for l in sums.splitlines() if l.strip().endswith(MODELS_ZIP)), None)
    h = hashlib.sha256()
    with open(zp, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    if want and want.lower() != h.hexdigest():
        zp.unlink()
        sys.exit("empreinte SHA-256 incorrecte : téléchargement corrompu, relancez la commande")
    print("empreinte SHA-256 %s" % ("vérifiée" if want else "non publiée"), flush=True)
    with zipfile.ZipFile(zp) as z:
        z.extractall(M)
    zp.unlink()
    print("modèles prêts dans", M)


def main():
    global M
    if "--dest" in sys.argv:                      # dossier de destination (défaut : models/ du dépôt)
        M = Path(sys.argv[sys.argv.index("--dest") + 1]).resolve()
    M.mkdir(parents=True, exist_ok=True)
    if "--prebuilt" in sys.argv:
        return prebuilt()
    # La conversion demande des paquets en plus : message clair s'il en manque un
    missing = []
    for mod, pkg in (("ctranslate2", "ctranslate2"), ("sentencepiece", "sentencepiece"), ("torch", "torch"),
                     ("transformers", "transformers"), ("huggingface_hub", "huggingface_hub")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        py = sys.executable
        sys.exit("Paquets manquants pour convertir les modèles : %s\n"
                 "Installez-les :\n"
                 "  \"%s\" -m pip install -r requirements.txt\n"
                 "  \"%s\" -m pip install torch --index-url https://download.pytorch.org/whl/cpu\n"
                 "  \"%s\" -m pip install transformers huggingface_hub\n"
                 "Ou, plus simple, sans conversion : \"%s\" scripts\\setup_models.py --prebuilt"
                 % (", ".join(missing), py, py, py, py))
    from huggingface_hub import hf_hub_download
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
