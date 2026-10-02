"""Point d'entrée de l'exécutable SallyTraduction.exe."""
import sys

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    if "--cli" in sys.argv:
        from sally_traduction.__main__ import cli
        sys.exit(cli(sys.argv[1:]))
    else:
        from sally_traduction.app import main
        main()
