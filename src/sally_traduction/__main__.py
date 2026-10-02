"""Point d'entrée : interface graphique, ou ligne de commande avec --cli.

    SallyTraduction.exe [fichier]
    SallyTraduction.exe --cli fichier1.pdf [fichier2.docx …] [--dir auto|en-fr|fr-en] [--out dossier] [--fast]

Codes de sortie en ligne de commande : 0 = tout est traduit, 1 = au moins un fichier en erreur, 2 = arguments invalides.
"""
import argparse
import sys


def attach_console():
    """L'exécutable est une application fenêtrée : en ligne de commande, on écrit dans la console appelante."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        import atexit
        import ctypes
        k32 = ctypes.windll.kernel32
        if not k32.AttachConsole(-1):              # ATTACH_PARENT_PROCESS
            return
        old_cp = k32.GetConsoleOutputCP()
        k32.SetConsoleOutputCP(65001)              # UTF-8 pour les accents
        atexit.register(k32.SetConsoleOutputCP, old_cp)
        out = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = out
        print()
    except Exception:
        pass


def cli(argv):
    attach_console()
    from pathlib import Path
    ap = argparse.ArgumentParser(prog="SallyTraduction")
    ap.add_argument("--cli", required=True, nargs="+", metavar="FICHIER")
    ap.add_argument("--dir", default="auto", choices=["auto", "en-fr", "fr-en"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--fast", action="store_true", help="sans deuxième avis M2M-100")
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    from .pipeline import Options, run
    last = {}

    def prog(stage, frac, msg):
        key = (stage, int(frac * 10))
        if last.get("k") != key:
            last["k"] = key
            print("[%-14s] %3d %%  %s" % (stage, frac * 100, msg), flush=True)

    errors = 0
    for f in a.cli:
        src = Path(f).resolve()
        out = a.out or str(src.parent)
        print("=== %s" % src.name, flush=True)
        try:
            r = run(src, out, Options(direction=a.dir, second_opinion=not a.fast), prog,
                    lambda m: print("  " + m, flush=True))
            print("Sortie       : %s" % r.output)
            print("Rapport      : %s" % r.report)
            print("Vérification : %s" % r.review)
            print("Résultat     : %d phrase(s) à relire sur %d, %.0f s" % (r.flagged, r.sentences, r.duration), flush=True)
        except Exception as e:
            errors += 1
            print("ERREUR : %s" % e, flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.exit(cli(sys.argv[1:]))
    else:
        from .app import main
        main()
