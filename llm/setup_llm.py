r"""Installe SallyTraduction-LLM : modèle Qwen3-30B-A3B (8 parties, 13 Go) et moteur llama.cpp portable.

    python llm\setup_llm.py                       # télécharge depuis la Release GitHub « llm-v1.0 »
    python llm\setup_llm.py --dossier E:\llm      # sans connexion : fichiers déjà copiés dans ce dossier

Chaque fichier est vérifié avec son empreinte SHA-256 ; un fichier déjà présent et correct n'est pas retéléchargé
(une coupure réseau se reprend en relançant simplement la commande). Aucun droit administrateur.
Résultat : llm\bin\llama-server.exe et llm\models\*.gguf
"""
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from setup_models import download, sha256   # noqa: E402  (proxy et certificats Windows, curl.exe en secours)

TAG = "llm-v1.0"
RELEASE = "https://github.com/salistar/SallyTraduction/releases/download/%s/" % TAG
SUMS = "SHA256SUMS-LLM.txt"
PARTS = "PARTS-LLM.txt"
LLAMA_ZIP = "llama.cpp-b11384-win-cpu-x64.zip"


def main():
    args = sys.argv[1:]
    local = Path(args[args.index("--dossier") + 1]).resolve() if "--dossier" in args else None
    cache = HERE / "telechargements"
    models, bindir = HERE / "models", HERE / "bin"
    for d in (cache, models, bindir):
        d.mkdir(parents=True, exist_ok=True)

    def fetch(name, label=None):
        dest = cache / name
        if local:
            src = local / name
            if not src.exists():
                raise SystemExit("fichier manquant dans %s : %s" % (local, name))
            if not dest.exists() or dest.stat().st_size != src.stat().st_size:
                print("copie :", name, flush=True)
                shutil.copyfile(src, dest)
        else:
            download(RELEASE + name, dest, label or name,
                     hint="placez tous les fichiers de la Release %s dans un dossier, puis :  python llm\\setup_llm.py "
                          "--dossier \"C:\\chemin\\du\\dossier\"" % TAG)
        return dest

    sums = {}
    for line in fetch(SUMS, "empreintes SHA-256").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            sums[parts[1]] = parts[0].lower()
    # Certains morceaux sont publiés en tranches de 256 Mo (PARTS-LLM.txt : morceau  tranche  sha256)
    pieces = {}
    try:
        for line in fetch(PARTS, "liste des tranches").read_text(encoding="utf-8").splitlines():
            p = line.split()
            if len(p) == 3 and not line.startswith("#"):
                pieces.setdefault(p[0], []).append((p[1], p[2].lower()))
    except SystemExit:
        pass

    def get_shard(name, label):
        """Renvoie le fichier du morceau, téléchargé d'un bloc ou recollé à partir de ses tranches."""
        if local and (local / name).exists() or name not in pieces:
            return fetch(name, label)
        out = cache / name
        with open(out, "wb") as dst:
            for j, (piece, digest) in enumerate(pieces[name], 1):
                for essai in range(1, 4):
                    f = fetch(piece, "%s, tranche %d/%d" % (label, j, len(pieces[name])))
                    if sha256(f) == digest:
                        break
                    f.unlink()
                else:
                    raise SystemExit("tranche corrompue : %s" % piece)
                with open(f, "rb") as src:
                    shutil.copyfileobj(src, dst, 1 << 20)
                f.unlink()
        return out

    shards = sorted(n for n in sums if n.endswith(".gguf"))
    total = len(shards)
    for k, name in enumerate(shards, 1):
        final = models / name
        if final.exists() and sha256(final) == sums[name]:
            print("[%d/%d] déjà installé : %s" % (k, total, name), flush=True)
            continue
        for essai in range(1, 4):
            f = get_shard(name, "[%d/%d] %s" % (k, total, name))
            if sha256(f) == sums[name]:
                f.replace(final)
                print("        empreinte vérifiée", flush=True)
                break
            print("        empreinte incorrecte (essai %d/3), nouveau téléchargement…" % essai, flush=True)
            f.unlink()
        else:
            raise SystemExit("téléchargement corrompu : %s" % name)

    exe = bindir / "llama-server.exe"
    if not exe.exists():
        z = fetch(LLAMA_ZIP, "moteur llama.cpp (18 Mo)")
        if sha256(z) != sums.get(LLAMA_ZIP):
            raise SystemExit("empreinte incorrecte : %s" % LLAMA_ZIP)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(bindir)
    for n in ("LICENSE-Qwen3-Apache-2.0.txt", "NOTICE-LLM.txt"):
        try:
            shutil.copyfile(fetch(n), models / n)
        except SystemExit:
            pass
    shutil.rmtree(cache, ignore_errors=True)
    print("\nSallyTraduction-LLM est prêt :")
    print("  moteur : %s" % exe)
    print("  modèle : %s (%d parties, %.1f Go)" % (models / shards[0], total,
          sum((models / s).stat().st_size for s in shards) / 2**30))


if __name__ == "__main__":
    main()
