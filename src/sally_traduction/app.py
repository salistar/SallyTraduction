"""Interface graphique SallyTraduction (CustomTkinter)."""
import os
import queue
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import APP_NAME, __version__
from .paths import assets_dir, model_available, model_path

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DND = True
except Exception:          # glisser-déposer facultatif
    _DND = False

# --------------------------------------------------------------------------
# Charte graphique (clair, sombre)
# --------------------------------------------------------------------------
BG = ("#F3F5FA", "#0A0F1E")
SIDEBAR = ("#FFFFFF", "#0E1528")
CARD = ("#FFFFFF", "#121A30")
CARD_ALT = ("#F1F4FB", "#172038")
BORDER = ("#E3E8F1", "#222D47")
INK = ("#0F172A", "#E8ECF7")
MUTED = ("#64748B", "#8D99B3")
ACCENT = ("#5B5BF0", "#6D6AF5")
ACCENT_HOVER = ("#4743D9", "#5A55E8")
ACCENT_SOFT = ("#ECECFE", "#1F2550")
OK = ("#059669", "#34D399")
WARN = ("#D97706", "#FBBF24")
BAD = ("#DC2626", "#F87171")

STEP_WEIGHTS = {"analyse": 0.03, "traduction": 0.22, "verification": 0.62, "reconstruction": 0.11, "rapport": 0.02}


def _family(*names):
    try:
        fams = set(tkfont.families())
    except Exception:
        fams = set()
    for n in names:
        if n in fams:
            return n
    return names[-1]


def _human_size(n):
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return ("%.0f %s" if unit in ("o", "Ko") else "%.1f %s") % (n, unit)
        n /= 1024


def _dur(s):
    s = int(max(0, s))
    if s >= 3600:
        return "%d h %02d min" % (s // 3600, s % 3600 // 60)
    if s >= 60:
        return "%d min %02d s" % (s // 60, s % 60)
    return "%d s" % s


def place_window(win, max_w, max_h, ratio_w=0.92, ratio_h=0.86):
    """Centre la fenêtre dans la zone de travail de l'écran (hors barre des tâches), mise à l'échelle comprise."""
    try:
        scale = ctk.ScalingTracker.get_window_scaling(win)
    except Exception:
        scale = 1.0
    try:                                   # zone de travail réelle (pixels physiques)
        import ctypes
        from ctypes import wintypes
        area = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(area), 0)
        sw, sh = (area.right - area.left) / scale, (area.bottom - area.top) / scale
    except Exception:
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    w, h = int(min(max_w, sw * ratio_w)), int(min(max_h, sh * ratio_h))
    win.geometry("%dx%d+%d+%d" % (w, h, max(0, (sw - w) / 2), max(0, (sh - h) / 2 - 20)))
    return w, h


def _open(path):
    try:
        os.startfile(str(path))
    except Exception as e:
        messagebox.showerror(APP_NAME, "Impossible d'ouvrir %s\n%s" % (path, e))


Base = (ctk.CTk, TkinterDnD.DnDWrapper) if _DND else (ctk.CTk,)


class App(*Base):
    def __init__(self, initial=None):
        super().__init__()
        self.dnd_ok = False
        if _DND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self.dnd_ok = True
            except Exception:
                pass
        ctk.set_appearance_mode("dark")
        self.title("%s — Traduction technique locale" % APP_NAME)
        w, h = place_window(self, 1240, 860)
        self.minsize(min(1080, w), min(640, h))
        self.configure(fg_color=BG)
        ico = assets_dir() / "icon.ico"
        if ico.exists():
            self.after(250, lambda: self.iconbitmap(str(ico)))

        disp = _family("Segoe UI Variable Display", "Segoe UI Semibold", "Segoe UI")
        text = _family("Segoe UI Variable Text", "Segoe UI")
        self.f_logo = ctk.CTkFont(disp, 22, "bold")
        self.f_h1 = ctk.CTkFont(disp, 28, "bold")
        self.f_h2 = ctk.CTkFont(disp, 15, "bold")
        self.f_body = ctk.CTkFont(text, 13)
        self.f_small = ctk.CTkFont(text, 12)
        self.f_tiny = ctk.CTkFont(text, 11, "bold")
        self.f_btn = ctk.CTkFont(disp, 15, "bold")
        self.f_big = ctk.CTkFont(disp, 30, "bold")

        self.file = None
        self.out_dir = tk.StringVar(value=str(Path.home() / "Documents" / "SallyTraduction"))
        self.direction = tk.StringVar(value="Détection auto")
        self.opt_back = tk.BooleanVar(value=True)
        self.opt_sem = tk.BooleanVar(value=True)
        self.opt_second = tk.BooleanVar(value=model_available("m2m100"))
        self.q = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.result = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._sidebar()
        self._main()
        self.after(100, self._poll)
        if initial:
            self._set_file(initial)
            if os.environ.get("SALLY_AUTOSTART") == "1":       # tests automatisés
                self.after(1500, self._start)
        if os.environ.get("SALLY_REVIEW"):                     # tests automatisés
            self.after(1200, lambda: self.open_review(os.environ["SALLY_REVIEW"]))

    # ------------------------------------------------------------------ UI
    def _card(self, master, **kw):
        return ctk.CTkFrame(master, fg_color=CARD, corner_radius=18, border_width=1, border_color=BORDER, **kw)

    def _sidebar(self):
        sb = ctk.CTkFrame(self, width=272, corner_radius=0, fg_color=SIDEBAR, border_width=0)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(sb, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=24, pady=(28, 4))
        logo = assets_dir() / "logo.png"
        if logo.exists():
            from PIL import Image
            img = ctk.CTkImage(Image.open(logo), size=(40, 40))
            ctk.CTkLabel(head, image=img, text="").pack(side="left", padx=(0, 12))
        names = ctk.CTkFrame(head, fg_color="transparent")
        names.pack(side="left")
        ctk.CTkLabel(names, text="Sally", font=self.f_logo, text_color=INK).pack(side="left")
        ctk.CTkLabel(names, text="Traduction", font=self.f_logo, text_color=ACCENT).pack(side="left")
        ctk.CTkLabel(sb, text="Traduction technique 100 % locale", font=self.f_small,
                     text_color=MUTED).grid(row=1, column=0, sticky="w", padx=24)

        ctk.CTkLabel(sb, text="MOTEURS", font=self.f_tiny, text_color=MUTED).grid(
            row=2, column=0, sticky="w", padx=24, pady=(34, 8))
        engines = [("opus-en-fr", "Opus-MT", "Anglais → Français"), ("opus-fr-en", "Opus-MT", "Français → Anglais"),
                   ("m2m100", "M2M-100 418M", "Deuxième avis"), ("minilm", "MiniLM multilingue", "Similarité"),
                   ("lid", "fastText LID", "Détection de langue")]
        box = ctk.CTkFrame(sb, fg_color=CARD_ALT, corner_radius=14)
        box.grid(row=3, column=0, sticky="ew", padx=16)
        from .engines import fasttext_available
        if not fasttext_available():                     # Python 3.13+ : détecteur intégré
            engines[-1] = ("lid", "Détecteur intégré", "Langue (anglais / français)")
        for i, (key, name, role) in enumerate(engines):
            ok = True if key == "lid" else model_available(key)
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=(12 if i == 0 else 4, 12 if i == len(engines) - 1 else 4))
            ctk.CTkLabel(row, text="●", font=self.f_small, text_color=OK if ok else BAD, width=14).pack(side="left")
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", padx=(8, 0))
            ctk.CTkLabel(col, text=name, font=self.f_body, text_color=INK, height=18, anchor="w").pack(anchor="w")
            ctk.CTkLabel(col, text=role, font=self.f_small, text_color=MUTED, height=16, anchor="w").pack(anchor="w")

        priv = ctk.CTkFrame(sb, fg_color=ACCENT_SOFT, corner_radius=14)
        priv.grid(row=4, column=0, sticky="ew", padx=16, pady=(18, 0))
        ctk.CTkLabel(priv, text="Confidentialité", font=self.f_h2, text_color=ACCENT).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(priv, text="Aucune connexion internet. Vos documents ne quittent jamais cet ordinateur.",
                     font=self.f_small, text_color=INK, wraplength=210, justify="left").pack(anchor="w", padx=16, pady=(0, 14))

        ctk.CTkButton(sb, text="Reprendre une vérification…", height=38, corner_radius=10, font=self.f_body,
                      fg_color="transparent", hover_color=CARD_ALT, text_color=INK, border_width=1,
                      border_color=BORDER, command=self._pick_review).grid(row=5, column=0, sticky="new", padx=16, pady=(14, 0))
        sb.grid_rowconfigure(5, weight=1)
        foot = ctk.CTkFrame(sb, fg_color="transparent")
        foot.grid(row=6, column=0, sticky="ew", padx=16, pady=20)
        ctk.CTkLabel(foot, text="Apparence", font=self.f_tiny, text_color=MUTED).pack(anchor="w", padx=8, pady=(0, 6))
        seg = ctk.CTkSegmentedButton(foot, values=["Sombre", "Clair"], command=self._theme, font=self.f_body,
                                     selected_color=ACCENT, selected_hover_color=ACCENT_HOVER, height=34,
                                     unselected_color=CARD_ALT, fg_color=CARD_ALT, text_color=INK)
        seg.set("Sombre")
        seg.pack(fill="x")
        ctk.CTkLabel(foot, text="Version %s" % __version__, font=self.f_small, text_color=MUTED).pack(anchor="w", padx=8, pady=(12, 0))

    def _main(self):
        main = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        self.main = main
        pad = dict(padx=36)

        hdr = ctk.CTkFrame(main, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(28, 18), **pad)
        ctk.CTkLabel(hdr, text="Traduire un document", font=self.f_h1, text_color=INK).pack(anchor="w")
        ctk.CTkLabel(hdr, text="PDF ou Word · anglais ⇄ français · mise en page conservée · contrôle qualité automatique",
                     font=self.f_body, text_color=MUTED).pack(anchor="w", pady=(2, 0))

        # Zone de dépôt
        self.drop = self._card(main, height=190)
        self.drop.grid(row=1, column=0, sticky="ew", **pad)
        self.drop.grid_propagate(False)
        self.drop.grid_columnconfigure(0, weight=1)
        self.drop.grid_rowconfigure(0, weight=1)
        self._drop_empty()

        # Réglages
        row = ctk.CTkFrame(main, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", pady=(18, 0), **pad)
        row.grid_columnconfigure((0, 1), weight=1, uniform="r")
        c1 = self._card(row)
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        ctk.CTkLabel(c1, text="Sens de traduction", font=self.f_h2, text_color=INK).pack(anchor="w", padx=22, pady=(18, 10))
        self.dir_btn = ctk.CTkSegmentedButton(
            c1, values=["Détection auto", "Anglais → Français", "Français → Anglais"], variable=self.direction,
            font=self.f_body, height=38, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=CARD_ALT, fg_color=CARD_ALT, text_color=INK, corner_radius=10)
        self.dir_btn.pack(fill="x", padx=22, pady=(0, 20))

        c2 = self._card(row)
        c2.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        ctk.CTkLabel(c2, text="Dossier de sortie", font=self.f_h2, text_color=INK).pack(anchor="w", padx=22, pady=(18, 10))
        line = ctk.CTkFrame(c2, fg_color="transparent")
        line.pack(fill="x", padx=22, pady=(0, 20))
        ctk.CTkEntry(line, textvariable=self.out_dir, height=38, font=self.f_body, fg_color=CARD_ALT,
                     border_color=BORDER, text_color=INK, corner_radius=10).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(line, text="Choisir", width=92, height=38, corner_radius=10, font=self.f_body,
                      fg_color=CARD_ALT, hover_color=BORDER, text_color=INK, border_width=1, border_color=BORDER,
                      command=self._pick_out).pack(side="left", padx=(10, 0))

        # Contrôles qualité
        qc = self._card(main)
        qc.grid(row=3, column=0, sticky="ew", pady=(18, 0), **pad)
        qc.grid_columnconfigure((0, 1, 2), weight=1, uniform="q")
        top = ctk.CTkFrame(qc, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=3, sticky="ew", padx=22, pady=(18, 4))
        ctk.CTkLabel(top, text="Contrôles qualité", font=self.f_h2, text_color=INK).pack(side="left")
        ctk.CTkLabel(top, text="  Langue, nombres et éléments techniques : toujours vérifiés", font=self.f_small,
                     text_color=MUTED).pack(side="left")
        checks = [(self.opt_back, "Retraduction", "Retraduit le résultat vers la langue d'origine et compare le sens."),
                  (self.opt_sem, "Similarité sémantique", "Mesure la proximité de sens entre chaque phrase et sa traduction."),
                  (self.opt_second, "Deuxième avis", "Un second traducteur indépendant (M2M-100) signale les désaccords.")]
        for i, (var, title, desc) in enumerate(checks):
            cell = ctk.CTkFrame(qc, fg_color=CARD_ALT, corner_radius=14)
            cell.grid(row=1, column=i, sticky="nsew", padx=(22 if i == 0 else 6, 22 if i == 2 else 6), pady=(8, 20))
            sw = ctk.CTkSwitch(cell, text=title, variable=var, font=self.f_h2, text_color=INK, progress_color=ACCENT,
                               button_color=("#FFFFFF", "#E8ECF7"), button_hover_color=("#FFFFFF", "#FFFFFF"))
            sw.pack(anchor="w", padx=16, pady=(14, 4))
            if i == 2 and not model_available("m2m100"):
                sw.configure(state="disabled")
            ctk.CTkLabel(cell, text=desc, font=self.f_small, text_color=MUTED, wraplength=240, justify="left").pack(
                anchor="w", padx=16, pady=(0, 14))

        # Actions
        act = ctk.CTkFrame(main, fg_color="transparent")
        act.grid(row=4, column=0, sticky="ew", pady=(22, 0), **pad)
        self.go = ctk.CTkButton(act, text="Lancer la traduction", font=self.f_btn, height=52, corner_radius=14,
                                fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#FFFFFF", command=self._start)
        self.go.pack(side="left", fill="x", expand=True)
        self.stop = ctk.CTkButton(act, text="Annuler", width=140, height=52, corner_radius=14, font=self.f_btn,
                                  fg_color="transparent", hover_color=CARD_ALT, text_color=BAD, border_width=1,
                                  border_color=BORDER, command=self._cancel)

        # Progression
        self.prog = self._card(main)
        self.prog.grid_columnconfigure(0, weight=1)
        steps = ctk.CTkFrame(self.prog, fg_color="transparent")
        steps.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 6))
        from .pipeline import STAGES
        self.step_widgets = {}
        for i, (key, label) in enumerate(STAGES):
            steps.grid_columnconfigure(i, weight=1, uniform="s")
            pill = ctk.CTkFrame(steps, fg_color=CARD_ALT, corner_radius=12)
            pill.grid(row=0, column=i, sticky="ew", padx=4)
            num = ctk.CTkLabel(pill, text=str(i + 1), width=26, height=26, corner_radius=13, fg_color=BORDER,
                               text_color=MUTED, font=self.f_tiny)
            num.pack(side="left", padx=(10, 8), pady=10)
            lab = ctk.CTkLabel(pill, text=label, font=self.f_small, text_color=MUTED, anchor="w")
            lab.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self.step_widgets[key] = (pill, num, lab)
        self.bar = ctk.CTkProgressBar(self.prog, height=10, corner_radius=5, progress_color=ACCENT, fg_color=CARD_ALT)
        self.bar.grid(row=1, column=0, sticky="ew", padx=26, pady=(12, 8))
        self.bar.set(0)
        info = ctk.CTkFrame(self.prog, fg_color="transparent")
        info.grid(row=2, column=0, sticky="ew", padx=26, pady=(0, 18))
        self.msg = ctk.CTkLabel(info, text="", font=self.f_body, text_color=INK)
        self.msg.pack(side="left")
        self.pct = ctk.CTkLabel(info, text="", font=self.f_h2, text_color=ACCENT)
        self.pct.pack(side="right")
        self.eta = ctk.CTkLabel(info, text="", font=self.f_small, text_color=MUTED)
        self.eta.pack(side="right", padx=16)

        # Résultat
        self.res = self._card(main)
        self.res.grid_columnconfigure(1, weight=1)

        # Journal
        self.log_card = self._card(main)
        ctk.CTkLabel(self.log_card, text="Journal", font=self.f_h2, text_color=INK).pack(anchor="w", padx=22, pady=(16, 6))
        self.log = ctk.CTkTextbox(self.log_card, height=130, font=ctk.CTkFont(_family("Cascadia Mono", "Consolas"), 12),
                                  fg_color=CARD_ALT, text_color=MUTED, corner_radius=12, border_width=0)
        self.log.pack(fill="x", padx=22, pady=(0, 20))
        self.log.configure(state="disabled")
        ctk.CTkFrame(main, fg_color="transparent", height=30).grid(row=9, column=0)

    # -------------------------------------------------------------- zone de dépôt
    def _clear_drop(self):
        for w in self.drop.winfo_children():
            w.destroy()

    def _register_drop(self, *widgets):
        if not self.dnd_ok:
            return
        for w in widgets:
            try:
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

    def _drop_empty(self):
        self._clear_drop()
        inner = ctk.CTkFrame(self.drop, fg_color=CARD_ALT, corner_radius=14, border_width=2, border_color=BORDER)
        inner.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure((0, 4), weight=1)
        icon = ctk.CTkLabel(inner, text="⇪", font=ctk.CTkFont(size=34, weight="bold"), text_color=ACCENT,
                            width=58, height=58, corner_radius=29, fg_color=ACCENT_SOFT)
        icon.grid(row=1, column=0, pady=(0, 8))
        t1 = ctk.CTkLabel(inner, text="Glissez-déposez votre fichier ici" if self.dnd_ok else "Sélectionnez votre fichier",
                          font=self.f_h2, text_color=INK)
        t1.grid(row=2, column=0)
        line = ctk.CTkFrame(inner, fg_color="transparent")
        line.grid(row=3, column=0, pady=(6, 0))
        t2 = ctk.CTkLabel(line, text="PDF ou Word (.docx)   ·   ", font=self.f_small, text_color=MUTED)
        t2.pack(side="left")
        ctk.CTkButton(line, text="Parcourir…", width=110, height=30, corner_radius=8, font=self.f_body,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._browse).pack(side="left")
        self._register_drop(self.drop, inner, icon, t1, line, t2)

    def _drop_file(self):
        self._clear_drop()
        p = self.file
        inner = ctk.CTkFrame(self.drop, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew", padx=26, pady=22)
        inner.grid_columnconfigure(1, weight=1)
        inner.grid_rowconfigure(0, weight=1)
        ext = p.suffix.lower().lstrip(".")
        badge = ctk.CTkLabel(inner, text=ext.upper(), width=86, height=104, corner_radius=14, font=self.f_big,
                             fg_color=("#FEE2E2", "#3B1520") if ext == "pdf" else ("#DBEAFE", "#132A4A"),
                             text_color=("#B91C1C", "#FCA5A5") if ext == "pdf" else ("#1D4ED8", "#93C5FD"))
        badge.grid(row=0, column=0, rowspan=2, padx=(0, 22))
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(info, text=p.name, font=self.f_h2, text_color=INK, anchor="w").pack(anchor="w")
        details = [_human_size(p.stat().st_size), "Document PDF" if ext == "pdf" else "Document Word"]
        if ext == "pdf":
            try:
                import pymupdf
                with pymupdf.open(p) as d:
                    details.insert(0, "%d pages" % d.page_count)
            except Exception:
                pass
        ctk.CTkLabel(info, text="   ·   ".join(details), font=self.f_body, text_color=MUTED).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(info, text=str(p.parent), font=self.f_small, text_color=MUTED).pack(anchor="w", pady=(2, 0))
        ctk.CTkButton(inner, text="Changer de fichier", width=150, height=36, corner_radius=10, font=self.f_body,
                      fg_color=CARD_ALT, hover_color=BORDER, text_color=INK, border_width=1, border_color=BORDER,
                      command=self._browse).grid(row=0, column=2, padx=(16, 0))
        self._register_drop(self.drop, inner, badge, info)

    def _on_drop(self, event):
        files = self.tk.splitlist(event.data)
        if files:
            self._set_file(files[0])

    def _browse(self):
        if self._busy():
            return
        f = filedialog.askopenfilename(title="Choisir un document",
                                       filetypes=[("Documents", "*.pdf *.docx"), ("PDF", "*.pdf"), ("Word", "*.docx")])
        if f:
            self._set_file(f)

    def _set_file(self, f):
        if self._busy():
            return
        p = Path(f).resolve()
        if p.suffix.lower() not in (".pdf", ".docx"):
            messagebox.showwarning(APP_NAME, "Format non pris en charge.\nChoisissez un fichier PDF ou Word (.docx).")
            return
        self.file = p
        self._drop_file()

    def _pick_out(self):
        d = filedialog.askdirectory(title="Dossier de sortie", initialdir=self.out_dir.get())
        if d:
            self.out_dir.set(d)

    def _pick_review(self):
        f = filedialog.askopenfilename(title="Reprendre une vérification", initialdir=self.out_dir.get(),
                                       filetypes=[("Vérification SallyTraduction", "*_verification.json")])
        if f:
            self.open_review(f)

    def open_review(self, path):
        from .review import ReviewWindow
        try:
            win = ReviewWindow(self, path)
            win.focus()
        except Exception as e:
            messagebox.showerror(APP_NAME, "Impossible d'ouvrir la vérification :\n%s" % e)

    def _theme(self, value):
        ctk.set_appearance_mode("dark" if value == "Sombre" else "light")
        if self.result is not None:
            self.after(50, self._draw_ring)

    # -------------------------------------------------------------- exécution
    def _busy(self):
        return self.worker is not None and self.worker.is_alive()

    def _start(self):
        if self._busy():
            return
        if not self.file:
            messagebox.showinfo(APP_NAME, "Choisissez d'abord un fichier PDF ou Word.")
            return
        if not (model_available("opus-en-fr") and model_available("opus-fr-en")):
            messagebox.showerror(APP_NAME, "Les modèles Opus-MT sont introuvables dans :\n%s" % model_path("opus-en-fr").parent)
            return
        from .pipeline import Options
        d = {"Détection auto": "auto", "Anglais → Français": "en-fr", "Français → Anglais": "fr-en"}[self.direction.get()]
        opts = Options(direction=d, backtranslation=self.opt_back.get(), semantic=self.opt_sem.get(),
                       second_opinion=self.opt_second.get())
        self.cancel.clear()
        self.result = None
        self.res.grid_forget()
        self.prog.grid(row=5, column=0, sticky="ew", pady=(18, 0), padx=36)
        self.log_card.grid(row=7, column=0, sticky="ew", pady=(18, 0), padx=36)
        self.stop.pack(side="left", padx=(12, 0))
        self.go.configure(state="disabled", text="Traduction en cours…")
        self.dir_btn.configure(state="disabled")
        for key, (pill, num, lab) in self.step_widgets.items():
            pill.configure(fg_color=CARD_ALT)
            num.configure(text=str(list(self.step_widgets).index(key) + 1), fg_color=BORDER, text_color=MUTED)
            lab.configure(text_color=MUTED)
        self.bar.set(0)
        self.pct.configure(text="0 %")
        self.eta.configure(text="")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.t0 = time.time()
        self.cur_stage = None
        self.worker = threading.Thread(target=self._work, args=(self.file, Path(self.out_dir.get()), opts), daemon=True)
        self.worker.start()

    def _work(self, path, out, opts):
        from . import pipeline
        from .engines import Cancelled
        try:
            r = pipeline.run(path, out, opts,
                             progress=lambda s, f, m: self.q.put(("progress", s, f, m)),
                             log=lambda m: self.q.put(("log", m)), cancel=self.cancel)
            self.q.put(("done", r))
        except Cancelled:
            self.q.put(("cancelled",))
        except Exception as e:
            import traceback
            self.q.put(("error", str(e), traceback.format_exc()))

    def _cancel(self):
        if self._busy():
            self.cancel.set()
            self.stop.configure(state="disabled", text="Arrêt…")

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                getattr(self, "_on_" + item[0])(*item[1:])
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _log(self, m):
        self.log.configure(state="normal")
        self.log.insert("end", time.strftime("%H:%M:%S  ") + m + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _on_log(self, m):
        self._log(m)

    def _on_progress(self, stage, frac, msg):
        keys = list(STEP_WEIGHTS)
        if stage != self.cur_stage:
            for k in keys[:keys.index(stage)]:
                pill, num, lab = self.step_widgets[k]
                num.configure(text="✓", fg_color=OK, text_color="#FFFFFF")
                lab.configure(text_color=INK)
            pill, num, lab = self.step_widgets[stage]
            pill.configure(fg_color=ACCENT_SOFT)
            num.configure(fg_color=ACCENT, text_color="#FFFFFF")
            lab.configure(text_color=INK)
            self.cur_stage = stage
        total = sum(STEP_WEIGHTS[k] for k in keys[:keys.index(stage)]) + STEP_WEIGHTS[stage] * frac
        self.bar.set(total)
        self.pct.configure(text="%d %%" % round(100 * total))
        self.msg.configure(text=msg)
        el = time.time() - self.t0
        if total > 0.05:
            self.eta.configure(text="Écoulé %s  ·  restant ≈ %s" % (_dur(el), _dur(el / total - el)))
        else:
            self.eta.configure(text="Écoulé %s" % _dur(el))

    def _finish_ui(self):
        self.stop.pack_forget()
        self.stop.configure(state="normal", text="Annuler")
        self.go.configure(state="normal", text="Lancer la traduction")
        self.dir_btn.configure(state="normal")

    def _on_cancelled(self):
        self._finish_ui()
        self.msg.configure(text="Traduction annulée.")
        self._log("Annulé par l'utilisateur.")

    def _on_error(self, msg, tb):
        self._finish_ui()
        self.msg.configure(text="Erreur : %s" % msg)
        self._log(tb)
        messagebox.showerror(APP_NAME, msg)

    def _on_done(self, r):
        self._finish_ui()
        self.result = r
        for k in STEP_WEIGHTS:
            pill, num, lab = self.step_widgets[k]
            pill.configure(fg_color=CARD_ALT)
            num.configure(text="✓", fg_color=OK, text_color="#FFFFFF")
            lab.configure(text_color=INK)
        self.bar.set(1)
        self.pct.configure(text="100 %")
        self.eta.configure(text="Durée %s" % _dur(r.duration))
        self.msg.configure(text="Traduction terminée")
        self._show_result()

    def _show_result(self):
        r = self.result
        for w in self.res.winfo_children():
            w.destroy()
        self.res.grid(row=6, column=0, sticky="ew", pady=(18, 0), padx=36)
        self.ring = tk.Canvas(self.res, width=180, height=180, highlightthickness=0, bd=0)
        self.ring.grid(row=0, column=0, rowspan=3, padx=(26, 18), pady=22)
        self._draw_ring()

        ctk.CTkLabel(self.res, text="Traduction terminée", font=self.f_h1, text_color=INK).grid(
            row=0, column=1, sticky="sw", pady=(24, 0))
        tone = OK if r.flagged == 0 else (WARN if r.flagged / max(1, r.sentences) < 0.1 else BAD)
        ctk.CTkLabel(self.res, text="%d phrase(s) à relire sur %d  ·  couverture %.1f %%  ·  %s"
                     % (r.flagged, r.sentences, 100 * r.coverage, _dur(r.duration)),
                     font=self.f_body, text_color=tone).grid(row=1, column=1, sticky="nw", pady=(2, 0))
        kp = ctk.CTkFrame(self.res, fg_color="transparent")
        kp.grid(row=2, column=1, sticky="ew", pady=(0, 6))
        for i, (lab, val) in enumerate([("Langue cible", "%.1f %%" % (100 * r.lang_ok)),
                                        ("Nombres conservés", "%.1f %%" % (100 * r.numbers_ok)),
                                        ("Similarité moyenne", "%.2f" % r.confidence),
                                        ("Sens", r.direction.replace("-", " → ").upper())]):
            box = ctk.CTkFrame(kp, fg_color=CARD_ALT, corner_radius=12)
            box.pack(side="left", padx=(0, 10))
            ctk.CTkLabel(box, text=lab, font=self.f_small, text_color=MUTED).pack(anchor="w", padx=14, pady=(10, 0))
            ctk.CTkLabel(box, text=val, font=self.f_h2, text_color=INK).pack(anchor="w", padx=14, pady=(0, 10))
        btns = ctk.CTkFrame(self.res, fg_color="transparent")
        btns.grid(row=3, column=0, columnspan=2, sticky="ew", padx=26, pady=(0, 22))
        if r.review and r.flagged:
            ctk.CTkButton(btns, text="Vérification manuelle (%d)" % r.flagged, height=44, corner_radius=12,
                          font=self.f_btn, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                          command=lambda: self.open_review(r.review)).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btns, text="Ouvrir le document traduit", height=44, corner_radius=12, font=self.f_btn,
                      fg_color=ACCENT if not r.flagged else "transparent", hover_color=ACCENT_HOVER if not r.flagged else CARD_ALT,
                      text_color="#FFFFFF" if not r.flagged else INK, border_width=0 if not r.flagged else 1,
                      border_color=BORDER, command=lambda: _open(r.output)).pack(side="left")
        for txt, target in (("Rapport de contrôle", r.report), ("Ouvrir le dossier", r.output.parent)):
            ctk.CTkButton(btns, text=txt, height=44, corner_radius=12, font=self.f_body, fg_color="transparent",
                          hover_color=CARD_ALT, text_color=INK, border_width=1, border_color=BORDER,
                          command=lambda t=target: _open(t)).pack(side="left", padx=(10, 0))
        self.after(100, lambda: self.main._parent_canvas.yview_moveto(1.0))

    def _draw_ring(self):
        r = self.result
        if r is None or not hasattr(self, "ring"):
            return
        dark = ctk.get_appearance_mode() == "Dark"
        bg = CARD[1] if dark else CARD[0]
        track = BORDER[1] if dark else BORDER[0]
        acc = ACCENT[1] if dark else ACCENT[0]
        ink = INK[1] if dark else INK[0]
        muted = MUTED[1] if dark else MUTED[0]
        score = (r.sentences - r.flagged) / max(1, r.sentences)
        c = self.ring
        c.configure(bg=bg)
        c.delete("all")
        c.create_oval(14, 14, 166, 166, outline=track, width=14)
        if score > 0:
            c.create_arc(14, 14, 166, 166, start=90, extent=-359.99 * score, style="arc", outline=acc, width=14)
        c.create_text(90, 82, text="%.1f %%" % (100 * score), fill=ink, font=(self.f_h1.cget("family"), 24, "bold"))
        c.create_text(90, 110, text="validées", fill=muted, font=(self.f_small.cget("family"), 11))


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Salistar.SallyTraduction")
        except Exception:
            pass
    initial = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    App(initial).mainloop()
