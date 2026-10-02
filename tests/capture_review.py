"""Ouvre la fenêtre de vérification manuelle et la capture."""
import ctypes, os, subprocess, sys, time
from ctypes import wintypes
from PIL import ImageGrab
ctypes.windll.user32.SetProcessDPIAware()
review, out = os.path.abspath(sys.argv[1]), sys.argv[2]
p = subprocess.Popen([r".venv\Scripts\python.exe", "-m", "sally_traduction"], cwd="src", env=dict(os.environ, SALLY_REVIEW=review))
hwnd, t0 = 0, time.time()
while not hwnd and time.time() - t0 < 40:
    time.sleep(0.5)
    hwnd = ctypes.windll.user32.FindWindowW(None, "Vérification manuelle — " + sys.argv[3])
time.sleep(3)
ctypes.windll.user32.SetForegroundWindow(hwnd); time.sleep(0.8)
r = wintypes.RECT(); ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
img = ImageGrab.grab((r.left, r.top, r.right, r.bottom), all_screens=True)
img.save(out)
print("capture", out, img.size, "pixel moyen", sum(img.convert("L").resize((1, 1)).getdata()))
p.terminate()
