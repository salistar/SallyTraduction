"""Lance l'interface, capture sa fenêtre puis la ferme (contrôle visuel)."""
import ctypes, subprocess, sys, time
from ctypes import wintypes
from PIL import ImageGrab
ctypes.windll.user32.SetProcessDPIAware()
out = sys.argv[1]
args = sys.argv[2:]
p = subprocess.Popen([r".venv\Scripts\python.exe", "-m", "sally_traduction"] + args, cwd="src")
hwnd = 0
for _ in range(60):
    time.sleep(0.5)
    hwnd = ctypes.windll.user32.FindWindowW(None, "SallyTraduction — Traduction technique locale")
    if hwnd:
        break
time.sleep(3)
r = wintypes.RECT()
ctypes.windll.user32.SetForegroundWindow(hwnd)
time.sleep(0.8)
ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
ImageGrab.grab((r.left, r.top, r.right, r.bottom), all_screens=True).save(out)
p.terminate()
print("capture", out, r.right - r.left, "x", r.bottom - r.top)
