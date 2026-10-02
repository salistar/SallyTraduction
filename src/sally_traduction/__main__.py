"""Point d'entrée : interface graphique, ou ligne de commande avec --cli.

    SallyTraduction.exe [fichier]
    SallyTraduction.exe --cli fichier.pdf [--dir auto|en-fr|fr-en] [--out dossier] [--fast]
"""
import argparse
import sys


def cli(argv):
    from .pipeline import Options, run
    ap = argparse.ArgumentParser(prog="SallyTraduction")
    ap.add_argument("--cli", required=True, metavar="FICHIER")
    ap.add_argument("--dir", default="auto", choices=["auto", "en-fr", "fr-en"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--fast", action="store_true", help="sans deuxième avis M2M-100")
    a = ap.parse_args(argv)
    from pathlib import Path
    out = a.out or str(Path(a.cli).resolve().parent)
    last = {}

    def prog(stage, frac, msg):
        key = (stage, int(frac * 10))
        if last.get("k") != key:
            last["k"] = key
            print("[%-14s] %3d %%  %s" % (stage, frac * 100, msg), flush=True)

    r = run(a.cli, out, Options(direction=a.dir, second_opinion=not a.fast), prog, lambda m: print("  " + m, flush=True))
    print("Sortie  :", r.output)
    print("Rapport :", r.report)


if __name__ == "__main__":
    if "--cli" in sys.argv:
        cli(sys.argv[1:])
    else:
        from .app import main
        main()
