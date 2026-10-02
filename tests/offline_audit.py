"""Traduit des documents en enregistrant toute tentative d'accès réseau (hook d'audit Python)."""
import sys
events = []
def hook(event, args):
    if event.startswith(("socket.", "urllib.Request", "http.client")) and event != "socket.__new__":
        events.append((event, repr(args)[:120]))
sys.addaudithook(hook)
from sally_traduction.pipeline import Options, run
for f in sys.argv[1:]:
    r = run(f, r"..\tests\out_offline", Options())
    print("OK", r.output.name, "-", r.flagged, "à relire sur", r.sentences)
print("Tentatives réseau :", len(events))
for e in events[:10]:
    print("  ", e)
