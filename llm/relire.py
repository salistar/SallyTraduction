r"""SallyTraduction-LLM : relecture des phrases signalées par un grand modèle de langage local (Qwen3-30B-A3B).

Lit le fichier *_verification.json produit par SallyTraduction, fait retraduire chaque phrase signalée par le
modèle (llama.cpp, 100 % local), puis régénère le document traduit, le rapport et la vérification.

    python llm\relire.py --verification "C:\...\document_FR_verification.json" [--sortie DOSSIER] [--rapide]
                         [--limite N] [--threads N] [--modele FICHIER.gguf] [--llama llama-server.exe]

Aucune connexion : llama-server écoute uniquement sur 127.0.0.1.
"""
import argparse
import csv
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from sally_traduction import protect                       # noqa: E402
from sally_traduction.pipeline import Options, _numbers, run   # noqa: E402

LANG = {"fr": "français", "en": "anglais"}
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # 127.0.0.1 : jamais via un proxy


# --------------------------------------------------------------------------
# Serveur llama.cpp local
# --------------------------------------------------------------------------
def find_model(arg):
    if arg:
        return Path(arg)
    shards = sorted((HERE / "models").glob("*-00001-of-*.gguf")) or sorted((HERE / "models").glob("*.gguf"))
    if not shards:
        raise SystemExit("Modèle introuvable dans llm\\models : lancez d'abord  python llm\\setup_llm.py")
    return shards[0]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LlamaServer:
    def __init__(self, exe, model, threads, ctx=4096):
        self.port = free_port()
        self.url = "http://127.0.0.1:%d" % self.port
        cmd = [str(exe), "-m", str(model), "--host", "127.0.0.1", "--port", str(self.port), "-c", str(ctx),
               "-np", "1", "--no-webui", "-t", str(threads)]
        self.log = open(HERE / "llama-server.log", "w", encoding="utf-8", errors="replace")
        flags = 0x08000000 if os.name == "nt" else 0              # CREATE_NO_WINDOW
        self.proc = subprocess.Popen(cmd, stdout=self.log, stderr=subprocess.STDOUT, creationflags=flags)

    def wait(self, timeout=900):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.proc.poll() is not None:
                raise SystemExit("llama-server s'est arrêté (voir llm\\llama-server.log) : RAM insuffisante ?")
            try:
                with NO_PROXY.open(self.url + "/health", timeout=3) as r:
                    if json.load(r).get("status") == "ok":
                        return time.time() - t0
            except Exception:
                pass
            time.sleep(2)
        raise SystemExit("le modèle ne s'est pas chargé en %d s" % timeout)

    def chat(self, system, user, max_tokens):
        body = json.dumps({"messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                           "temperature": 0.15, "top_p": 0.8, "max_tokens": max_tokens}).encode("utf-8")
        req = urllib.request.Request(self.url + "/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        with NO_PROXY.open(req, timeout=1800) as r:
            d = json.load(r)
        return d["choices"][0]["message"]["content"], d.get("usage", {}).get("completion_tokens", 0)

    def stop(self):
        try:
            self.proc.terminate()
            self.proc.wait(20)
        except Exception:
            self.proc.kill()
        self.log.close()


# --------------------------------------------------------------------------
# Relecture
# --------------------------------------------------------------------------
def build_prompt(src, opus, src_lang, tgt_lang, glossary):
    system = ("Tu es un traducteur technique professionnel, spécialiste de l'informatique, du DevOps, de la "
              "sécurité et des paiements. Tu traduis du %s vers le %s de façon fidèle, précise et naturelle.\n"
              "Règles :\n"
              "1. N'ajoute aucune information et n'en omets aucune.\n"
              "2. Recopie à l'identique les éléments techniques indiqués (commandes, chemins, identifiants, "
              "options), ainsi que tous les nombres.\n"
              "3. Respecte le glossaire imposé.\n"
              "4. Réponds uniquement par la traduction finale, sur une seule ligne, sans guillemets ni commentaire."
              % (LANG[src_lang], LANG[tgt_lang]))
    _, values = protect.protect(src, [])
    tech = [v for v in values if not isinstance(v, protect.Term)]
    gl = []
    for rx, dst in glossary:
        m = rx.search(src)
        if m:
            gl.append("%s → %s" % (m.group(0), dst))
    user = "PHRASE SOURCE (%s) :\n%s\n\nTRADUCTION AUTOMATIQUE À CORRIGER :\n%s\n" % (LANG[src_lang], src, opus)
    if gl:
        user += "\nGLOSSAIRE IMPOSÉ :\n" + "\n".join(gl) + "\n"
    if tech:
        user += "\nÉLÉMENTS À GARDER TELS QUELS :\n" + "\n".join(tech) + "\n"
    user += "\nTRADUCTION CORRIGÉE EN %s :" % LANG[tgt_lang].upper()
    return system, user, tech


def clean(text):
    t = text.strip()
    t = re.sub(r"^(traduction( corrigée)?( en \w+)?|translation)\s*:\s*", "", t, flags=re.I)
    t = t.splitlines()[0].strip() if t else t
    if len(t) >= 2 and t[0] in "\"«“'" and t[-1] in "\"»”'":
        t = t[1:-1].strip()
    return t


def validate(src, cand, tech):
    if not cand:
        return "réponse vide"
    ratio = len(cand) / max(1, len(src))
    if ratio > 3 or ratio < 0.3:
        return "longueur anormale"
    missing = [t for t in tech if t not in cand]
    if missing:
        return "élément technique modifié : " + ", ".join(missing[:2])
    if _numbers(src) != _numbers(cand):
        return "nombres différents"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verification", required=True, help="fichier *_verification.json de SallyTraduction")
    ap.add_argument("--sortie", help="dossier du document relu (défaut : à côté du document traduit)")
    ap.add_argument("--rapide", action="store_true", help="contrôles finaux sans le deuxième avis M2M-100")
    ap.add_argument("--limite", type=int, default=0, help="nombre maximal de phrases à relire (test)")
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 4) // 2))
    ap.add_argument("--modele")
    ap.add_argument("--llama", default=str(HERE / "bin" / "llama-server.exe"))
    a = ap.parse_args()

    vpath = Path(a.verification).resolve()
    data = json.loads(vpath.read_text(encoding="utf-8"))
    source = Path(data["source"])
    if not source.exists():
        raise SystemExit("document source introuvable : %s" % source)
    src_lang, tgt_lang = data["direction"].split("-")
    rows = data["rows"][: a.limite] if a.limite else data["rows"]
    if not rows:
        print("Aucune phrase signalée : rien à relire.")
        return 0
    exe, model = Path(a.llama), find_model(a.modele)
    if not exe.exists():
        raise SystemExit("llama-server introuvable (%s) : lancez d'abord  python llm\\setup_llm.py" % exe)

    print("Relecture de %d phrase(s) par %s (%s → %s)" % (len(rows), model.name.split("-0000")[0], src_lang, tgt_lang),
          flush=True)
    server = LlamaServer(exe, model, a.threads)
    corrections, journal = {}, []
    try:
        print("Chargement du modèle…", flush=True)
        print("Modèle prêt en %.0f s." % server.wait(), flush=True)
        glossary = protect.load_glossary(data["direction"])
        t0, tokens = time.time(), 0
        for k, r in enumerate(rows, 1):
            system, user, tech = build_prompt(r["src"], r["tgt"], src_lang, tgt_lang, glossary)
            reply, n = server.chat(system, user, max_tokens=int(len(r["src"]) * 0.8) + 64)
            tokens += n
            cand = clean(reply)
            why = validate(r["src"], cand, tech)
            if why is None:
                corrections[r["src"]] = cand
            journal.append(dict(n=r.get("id", k), src=r["src"], opus=r["tgt"], llm=cand,
                                statut="retenue" if why is None else "rejetée (%s)" % why))
            el = time.time() - t0
            print("[%d/%d] %s  %.1f tokens/s  reste ≈ %d min" % (k, len(rows), "✓" if why is None else "✗ " + why,
                  tokens / max(el, 1e-9), el / k * (len(rows) - k) / 60), flush=True)
    finally:
        server.stop()

    out_dir = Path(a.sortie) if a.sortie else Path(data["output"]).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    print("\n%d correction(s) retenue(s) sur %d. Régénération du document…" % (len(corrections), len(rows)), flush=True)

    def prog(stage, frac, msg, last={}):
        key = (stage, int(frac * 4))
        if last.get("k") != key:
            last["k"] = key
            print("[%-14s] %3d %%  %s" % (stage, frac * 100, msg), flush=True)

    res = run(source, out_dir, Options(direction=data["direction"], second_opinion=not a.rapide,
                                       overrides=corrections, out_suffix="_LLM"),
              prog, lambda m: print("  " + m, flush=True))
    final, report, review = res.output, res.report, res.review
    log = final.with_name(final.stem + "_corrections.csv")
    with open(log, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["N°", "Statut", "Original", "Traduction Opus-MT", "Traduction relue (LLM)"])
        for j in journal:
            w.writerow([j["n"], j["statut"], j["src"], j["opus"], j["llm"]])
    print("\nDocument relu      : %s" % final)
    print("Rapport            : %s" % report)
    print("Vérification       : %s" % review)
    print("Journal des corrections : %s" % log)
    avant = sum(len(r.get("locations", [1])) for r in data["rows"])
    print("Phrases encore à relire : %d (avant relecture : %d)" % (res.flagged, avant))
    return 0


if __name__ == "__main__":
    sys.exit(main())
