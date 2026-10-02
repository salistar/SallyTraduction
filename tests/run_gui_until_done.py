"""Lance l'interface en démarrage automatique et attend le rapport (test sans capture d'écran)."""
import os, subprocess, sys, time, glob
out = os.path.join(os.path.expanduser("~"), "Documents", "SallyTraduction")
before = set(glob.glob(os.path.join(out, "*")))
p = subprocess.Popen([r".venv\Scripts\python.exe", "-m", "sally_traduction", sys.argv[1]], cwd="src",
                     env=dict(os.environ, SALLY_AUTOSTART="1"))
t0 = time.time()
while time.time() - t0 < 1200:
    time.sleep(5)
    new = set(glob.glob(os.path.join(out, "*"))) - before
    if any(f.endswith("_rapport.html") for f in new):
        print("terminé en %.0f s :" % (time.time() - t0), sorted(os.path.basename(f) for f in new))
        break
    if p.poll() is not None:
        print("l'application s'est fermée, code", p.returncode)
        break
else:
    print("délai dépassé")
time.sleep(3)
p.terminate()
