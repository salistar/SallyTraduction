"""Lance une traduction dans l'interface et capture la fenêtre à plusieurs instants."""
import ctypes, os, subprocess, sys, time
from ctypes import wintypes
from PIL import ImageGrab
ctypes.windll.user32.SetProcessDPIAware()
doc, shots = sys.argv[1], [(float(t), name) for t, name in (a.split("=") for a in sys.argv[2:])]
env = dict(os.environ, SALLY_AUTOSTART="1")
p = subprocess.Popen([r".venv\Scripts\python.exe", "-m", "sally_traduction", doc], cwd="src", env=env)
t0 = time.time()
hwnd = 0
while not hwnd and time.time() - t0 < 30:
    time.sleep(0.5)
    hwnd = ctypes.windll.user32.FindWindowW(None, "SallyTraduction — Traduction technique locale")
for t, name in shots:
    while time.time() - t0 < t:
        time.sleep(0.5)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    time.sleep(0.6)
    r = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
    ImageGrab.grab((r.left, r.top, r.right, r.bottom), all_screens=True).save(name)
    print("capture", name, "à", round(time.time() - t0), "s")
p.terminate()
