"""Prépare les modèles dans models/ (à lancer une fois après le clonage du dépôt).

    python scripts/setup_models.py                 # convertit les originaux (Hugging Face) ; si huggingface.co
                                                   # est injoignable, bascule seul sur les modèles convertis (GitHub)
    python scripts/setup_models.py --prebuilt      # modèles déjà convertis depuis GitHub (635 Mo), sans PyTorch
    python scripts/setup_models.py --zip FICHIER   # depuis un SallyTraduction-Models.zip déjà téléchargé
                                                   # (navigateur, clé USB…) : aucune connexion
    option --dest DOSSIER                          # autre dossier que models/

Réseau d'entreprise : le téléchargement GitHub utilise le proxy et les certificats de Windows, puis curl.exe en secours.
La conversion demande : pip install ctranslate2 sentencepiece torch transformers huggingface_hub
"""
import hashlib
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

RELEASE = "https://github.com/salistar/SallyTraduction/releases/latest/download/"
MODELS_ZIP = "SallyTraduction-Models.zip"
MODEL_DIRS = ("opus-mt-en-fr-ct2", "opus-mt-fr-en-ct2", "m2m100_418m-ct2", "minilm", "lid")

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "models"


class HubUnreachable(Exception):
    pass


# --------------------------------------------------------------------------
# Téléchargement (proxy et certificats Windows, curl.exe en secours)
# --------------------------------------------------------------------------
def _windows_ssl_context():
    import ssl
    ctx = ssl.create_default_context()
    try:
        ctx.load_default_certs()            # magasin de certificats Windows (proxy d'entreprise compris)
    except Exception:
        pass
    return ctx


def download(url, dest, label, hint=None):
    print("téléchargement :", label, flush=True)
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler(),   # proxy Windows / variables HTTPS_PROXY
                                             urllib.request.HTTPSHandler(context=_windows_ssl_context()))
        with opener.open(url, timeout=60) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done, step = 0, 0
            while True:
                block = r.read(1 << 20)
                if not block:
                    break
                f.write(block)
                done += len(block)
                if total and done * 10 // total > step:
                    step = done * 10 // total
                    print("  %3d %%" % (step * 10), flush=True)
        return
    except Exception as e:
        print("  Python n'a pas pu télécharger (%s) : essai avec curl.exe…" % e.__class__.__name__, flush=True)
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if curl and subprocess.call([curl, "-L", "--fail", "--ssl-no-revoke", "--progress-bar", "-o", str(dest), url]) == 0:
        return
    raise SystemExit("Téléchargement impossible : %s\nTéléchargez le fichier avec votre navigateur, puis :\n  %s"
                     % (url, hint or "\"%s\" scripts\\setup_models.py --zip \"C:\\chemin\\vers\\%s\""
                        % (sys.executable, MODELS_ZIP)))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def install_zip(zp):
    with zipfile.ZipFile(zp) as z:
        names = {n.split("/")[0] for n in z.namelist()}
        if not {"opus-mt-en-fr-ct2", "opus-mt-fr-en-ct2"} <= names:
            raise SystemExit("%s ne contient pas les modèles SallyTraduction" % zp)
        z.extractall(M)
    print("modèles prêts dans", M)


def prebuilt():
    """Modèles déjà convertis depuis la dernière Release GitHub, empreinte SHA-256 vérifiée."""
    zp = M / MODELS_ZIP
    download(RELEASE + MODELS_ZIP, zp, MODELS_ZIP + " (635 Mo) depuis GitHub")
    sums = M / "SHA256SUMS.txt"
    want = None
    try:
        download(RELEASE + "SHA256SUMS.txt", sums, "empreintes SHA-256")
        want = next((l.split()[0] for l in sums.read_text().splitlines() if l.strip().endswith(MODELS_ZIP)), None)
        sums.unlink()
    except SystemExit:
        pass
    if want and want.lower() != sha256(zp):
        zp.unlink()
        raise SystemExit("empreinte SHA-256 incorrecte : téléchargement corrompu, relancez la commande")
    print("empreinte SHA-256 %s" % ("vérifiée" if want else "non vérifiée"), flush=True)
    install_zip(zp)
    zp.unlink()


# --------------------------------------------------------------------------
# Conversion depuis les modèles d'origine (Hugging Face)
# --------------------------------------------------------------------------
def hub_reachable():
    try:
        from huggingface_hub import model_info
        model_info("Helsinki-NLP/opus-mt-en-fr", timeout=15)
        return True
    except Exception:
        return False


def ct2(model, out, extra):
    if (M / out / "model.bin").exists():
        print("déjà présent :", out)
        return
    print("conversion :", model, "->", out, flush=True)
    from ctranslate2.converters import TransformersConverter
    TransformersConverter(model, copy_files=extra, low_cpu_mem_usage=True).convert(
        str(M / out), quantization="int8", force=True)


def convert():
    missing = []
    for mod in ("ctranslate2", "sentencepiece", "torch", "transformers", "huggingface_hub"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        py = sys.executable
        raise SystemExit("Paquets manquants pour convertir les modèles : %s\n"
                         "Installez-les :\n"
                         "  \"%s\" -m pip install -r requirements.txt\n"
                         "  \"%s\" -m pip install torch --index-url https://download.pytorch.org/whl/cpu\n"
                         "  \"%s\" -m pip install transformers huggingface_hub\n"
                         "Ou, plus simple, sans conversion : \"%s\" scripts\\setup_models.py --prebuilt"
                         % (", ".join(missing), py, py, py, py))
    if not hub_reachable():
        raise HubUnreachable()
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
        try:
            download("https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz", lid, "fastText lid.176")
        except SystemExit:
            print("fastText indisponible : le détecteur de langue intégré sera utilisé.")
    print("modèles prêts dans", M)


def main():
    global M
    args = sys.argv[1:]
    if "--dest" in args:                          # dossier de destination (défaut : models/ du dépôt)
        M = Path(args[args.index("--dest") + 1]).resolve()
    M.mkdir(parents=True, exist_ok=True)
    if "--zip" in args:
        zp = Path(args[args.index("--zip") + 1]).resolve()
        if not zp.exists():
            raise SystemExit("fichier introuvable : %s" % zp)
        return install_zip(zp)
    if "--prebuilt" in args:
        return prebuilt()
    try:
        convert()
    except HubUnreachable:
        print("\nhuggingface.co est injoignable (pare-feu ou proxy d'entreprise ?).\n"
              "Bascule automatique : modèles déjà convertis depuis GitHub.\n", flush=True)
        prebuilt()
    missing = [d for d in MODEL_DIRS[:4] if not (M / d).exists()]
    if missing:
        raise SystemExit("modèles manquants : %s" % ", ".join(missing))


if __name__ == "__main__":
    main()
