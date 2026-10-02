"""Fenêtre « Vérification manuelle » : phrases signalées avec page, ligne et position du mot."""
import csv
import json
import os
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import APP_NAME
from .paths import assets_dir
from .app import (ACCENT, ACCENT_HOVER, ACCENT_SOFT, BG, BORDER, CARD, CARD_ALT, INK, MUTED, OK, WARN, BAD,
                  place_window)

PER_PAGE = 20


class ReviewWindow(ctk.CTkToplevel):
    def __init__(self, master, review_path):
        super().__init__(master)
        self.app = master
        self.path = Path(review_path)
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.rows = self.data["rows"]
        self.output = Path(self.data["output"])
        self.is_pdf = self.data.get("kind") == "pdf"
        self.page = 0
        self._save_job = None

        self.title("Vérification manuelle — %s" % self.output.name)
        self.configure(fg_color=BG)
        self.win_w, _ = place_window(self, 1280, 900, 0.94, 0.9)
        self.minsize(900, 560)
        self.after(250, self.lift)
        ico = assets_dir() / "icon.ico"
        if ico.exists():
            self.after(300, lambda: self.iconbitmap(str(ico)))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        f = master
        self.f_h1, self.f_h2, self.f_body, self.f_small, self.f_tiny = f.f_h1, f.f_h2, f.f_body, f.f_small, f.f_tiny

        # En-tête
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 8))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="Vérification manuelle", font=self.f_h1, text_color=INK).grid(row=0, column=0, sticky="w")
        how = ("Emplacements : page du PDF (numérotation du lecteur PDF), ligne comptée depuis le haut de la page, "
               "mot compté depuis le début de la ligne." if self.is_pdf else
               "Emplacements : partie du document, numéro de paragraphe non vide, mot compté depuis le début du paragraphe.")
        ctk.CTkLabel(head, text=how, font=self.f_small, text_color=MUTED).grid(row=1, column=0, sticky="w", pady=(2, 0))
        right = ctk.CTkFrame(head, fg_color="transparent")
        right.grid(row=0, column=1, rowspan=2, sticky="e")
        self.count = ctk.CTkLabel(right, text="", font=self.f_h2, text_color=INK)
        self.count.pack(anchor="e")
        self.bar = ctk.CTkProgressBar(right, width=240, height=8, progress_color=OK, fg_color=CARD_ALT)
        self.bar.pack(anchor="e", pady=(6, 0))

        # Barre d'outils
        tb = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        tb.grid(row=1, column=0, sticky="ew", padx=28, pady=(8, 10))
        # (pas de textvariable : CustomTkinter n'affiche le texte d'aide que sans variable liée)
        self.q = ctk.CTkEntry(tb, placeholder_text="Rechercher dans l'original ou la traduction…",
                              height=36, font=self.f_body, fg_color=CARD_ALT, border_color=BORDER, text_color=INK,
                              placeholder_text_color=MUTED, corner_radius=10)
        self.q.pack(side="left", fill="x", expand=True, padx=(14, 8), pady=12)
        self.q.bind("<KeyRelease>", lambda ev: self._refresh(reset=True))
        reasons = sorted({r.split(" (")[0].split(" :")[0] for row in self.rows for r in row["reasons"]})
        self.reason = ctk.StringVar(value="Tous les motifs")
        ctk.CTkOptionMenu(tb, values=["Tous les motifs"] + reasons, variable=self.reason, height=36, width=230,
                          font=self.f_body, fg_color=CARD_ALT, button_color=CARD_ALT, button_hover_color=BORDER,
                          text_color=INK, dropdown_font=self.f_body,
                          command=lambda v: self._refresh(reset=True)).pack(side="left", padx=4)
        self.status = ctk.StringVar(value="À vérifier")
        ctk.CTkSegmentedButton(tb, values=["À vérifier", "Vérifiées", "Toutes"], variable=self.status, height=36,
                               font=self.f_body, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
                               unselected_color=CARD_ALT, fg_color=CARD_ALT, text_color=INK,
                               command=lambda v: self._refresh(reset=True)).pack(side="left", padx=8)
        ctk.CTkButton(tb, text="Exporter (CSV)", height=36, width=130, corner_radius=10, font=self.f_body,
                      fg_color="transparent", hover_color=CARD_ALT, text_color=INK, border_width=1,
                      border_color=BORDER, command=self._export).pack(side="left", padx=(4, 14))

        # Liste
        self.list = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        self.list.grid(row=2, column=0, sticky="nsew", padx=18)
        self.list.grid_columnconfigure(0, weight=1)

        # Pagination
        pg = ctk.CTkFrame(self, fg_color="transparent")
        pg.grid(row=3, column=0, sticky="ew", padx=28, pady=12)
        self.prev = ctk.CTkButton(pg, text="◀  Précédent", width=130, height=36, corner_radius=10, font=self.f_body,
                                  fg_color=CARD_ALT, hover_color=BORDER, text_color=INK, command=lambda: self._go(-1))
        self.prev.pack(side="left")
        self.pinfo = ctk.CTkLabel(pg, text="", font=self.f_body, text_color=MUTED)
        self.pinfo.pack(side="left", expand=True)
        self.next = ctk.CTkButton(pg, text="Suivant  ▶", width=130, height=36, corner_radius=10, font=self.f_body,
                                  fg_color=CARD_ALT, hover_color=BORDER, text_color=INK, command=lambda: self._go(1))
        self.next.pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._refresh()

    # ------------------------------------------------------------------ données
    def _filtered(self):
        q = self.q.get().strip().lower() if hasattr(self, "q") else ""
        reason, status = self.reason.get(), self.status.get()
        out = []
        for r in self.rows:
            if status == "À vérifier" and r.get("checked"):
                continue
            if status == "Vérifiées" and not r.get("checked"):
                continue
            if reason != "Tous les motifs" and not any(x.startswith(reason) for x in r["reasons"]):
                continue
            if q and q not in (r["src"] + " " + r["tgt"] + " " + r.get("note", "")).lower():
                continue
            out.append(r)
        return out

    def _save_soon(self):
        if self._save_job:
            self.after_cancel(self._save_job)
        self._save_job = self.after(400, self._save)

    def _save(self):
        self._save_job = None
        try:
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:
            messagebox.showerror(APP_NAME, "Impossible d'enregistrer la vérification :\n%s" % e, parent=self)

    def _close(self):
        if self._save_job:
            self.after_cancel(self._save_job)
            self._save()
        self.destroy()

    # ------------------------------------------------------------------ affichage
    def _go(self, d):
        self.page += d
        self._refresh()

    def _refresh(self, reset=False):
        if reset:
            self.page = 0
        done = sum(1 for r in self.rows if r.get("checked"))
        self.count.configure(text="%d / %d phrase(s) vérifiée(s)" % (done, len(self.rows)))
        self.bar.set(done / len(self.rows) if self.rows else 1)
        items = self._filtered()
        pages = max(1, (len(items) + PER_PAGE - 1) // PER_PAGE)
        self.page = max(0, min(self.page, pages - 1))
        self.prev.configure(state="normal" if self.page > 0 else "disabled")
        self.next.configure(state="normal" if self.page < pages - 1 else "disabled")
        self.pinfo.configure(text="Page %d / %d  ·  %d phrase(s)" % (self.page + 1, pages, len(items)))
        for w in self.list.winfo_children():
            w.destroy()
        if not items:
            msg = "Toutes les phrases ont été vérifiées. Bravo !" if self.rows and done == len(self.rows) else "Aucune phrase."
            ctk.CTkLabel(self.list, text=msg, font=self.f_h2, text_color=MUTED).grid(row=0, column=0, pady=60)
            return
        for k, r in enumerate(items[self.page * PER_PAGE:(self.page + 1) * PER_PAGE]):
            self._card(k, r)
        try:
            self.list._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def _card(self, k, r):
        card = ctk.CTkFrame(self.list, fg_color=CARD, corner_radius=14, border_width=1,
                            border_color=OK if r.get("checked") else BORDER)
        card.grid(row=k, column=0, sticky="ew", padx=10, pady=6)
        card.grid_columnconfigure((0, 1), weight=1, uniform="c")
        loc = r["locations"][0]

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(12, 6))
        ctk.CTkLabel(top, text="#%d" % r["id"], font=self.f_tiny, text_color=MUTED).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(top, text="  %s  " % loc["tgt_label"], font=self.f_body, text_color=ACCENT, fg_color=ACCENT_SOFT,
                     corner_radius=8, height=26).pack(side="left")
        if len(r["locations"]) > 1:
            others = ", ".join(l["tgt_label"] for l in r["locations"][1:4])
            more = " …" if len(r["locations"]) > 4 else ""
            ctk.CTkLabel(top, text="  aussi : %s%s" % (others, more), font=self.f_small, text_color=MUTED).pack(side="left")
        var = ctk.BooleanVar(value=bool(r.get("checked")))

        def toggle():
            r["checked"] = var.get()
            card.configure(border_color=OK if r["checked"] else BORDER)
            self._save_soon()
            done = sum(1 for x in self.rows if x.get("checked"))
            self.count.configure(text="%d / %d phrase(s) vérifiée(s)" % (done, len(self.rows)))
            self.bar.set(done / len(self.rows))
        ctk.CTkCheckBox(top, text="Vérifiée", variable=var, command=toggle, font=self.f_body, text_color=INK,
                        fg_color=OK, hover_color=OK, border_color=BORDER).pack(side="right")

        chips = ctk.CTkFrame(card, fg_color="transparent")
        chips.grid(row=1, column=0, columnspan=2, sticky="w", padx=16)
        for reason in r["reasons"]:
            bad = any(x in reason for x in ("vide", "non traduite", "Langue", "perdu"))
            ctk.CTkLabel(chips, text="  %s  " % reason, font=self.f_small, text_color=BAD if bad else WARN,
                         fg_color=CARD_ALT, corner_radius=8, height=22).pack(side="left", padx=(0, 6))

        wrap = max(300, int(self.win_w / 2) - 120)
        for col, (title, text) in enumerate((("ORIGINAL — %s" % loc["src_label"], r["src"]),
                                             ("TRADUCTION — %s" % loc["tgt_label"], r["tgt"]))):
            box = ctk.CTkFrame(card, fg_color=CARD_ALT, corner_radius=10)
            box.grid(row=2, column=col, sticky="nsew", padx=(16 if col == 0 else 6, 6 if col == 0 else 16), pady=10)
            ctk.CTkLabel(box, text=title, font=self.f_tiny, text_color=MUTED, anchor="w").pack(anchor="w", padx=12, pady=(8, 2))
            ctk.CTkLabel(box, text=text, font=self.f_body, text_color=INK, wraplength=wrap, justify="left",
                         anchor="w").pack(anchor="w", padx=12, pady=(0, 10))
        extra = []
        if r.get("alt"):
            extra.append("Second traducteur : " + r["alt"])
        if r.get("back"):
            extra.append("Retraduction : " + r["back"])
        if extra:
            ctk.CTkLabel(card, text="\n".join(extra), font=self.f_small, text_color=MUTED, justify="left",
                         wraplength=wrap * 2, anchor="w").grid(row=3, column=0, columnspan=2, sticky="w", padx=18)

        bot = ctk.CTkFrame(card, fg_color="transparent")
        bot.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 14))
        ent = ctk.CTkEntry(bot, placeholder_text="Note ou correction proposée…", height=34, font=self.f_body,
                           fg_color=CARD_ALT, border_color=BORDER, text_color=INK, placeholder_text_color=MUTED,
                           corner_radius=8)
        ent.pack(side="left", fill="x", expand=True)
        if r.get("note"):
            ent.insert(0, r["note"])

        def save_note(*_):
            if r.get("note", "") != ent.get():
                r["note"] = ent.get()
                self._save_soon()
        ent.bind("<KeyRelease>", save_note)
        ent.bind("<FocusOut>", save_note)
        btn = dict(height=34, corner_radius=8, font=self.f_small, fg_color="transparent", hover_color=CARD_ALT,
                   text_color=INK, border_width=1, border_color=BORDER)
        if self.is_pdf:
            ctk.CTkButton(bot, text="Ouvrir à la page %d" % loc["tgt"]["page"], width=150,
                          command=lambda: self._open_page(loc["tgt"]["page"]), **btn).pack(side="left", padx=(8, 0))
        ctk.CTkButton(bot, text="Copier la traduction", width=150,
                      command=lambda: self._copy(r["tgt"]), **btn).pack(side="left", padx=(8, 0))
        ctk.CTkButton(bot, text="Copier l'emplacement", width=160,
                      command=lambda: self._copy("%s — %s" % (self.output.name, loc["tgt_label"])), **btn).pack(side="left", padx=(8, 0))

    # ------------------------------------------------------------------ actions
    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _open_page(self, page):
        if not self.output.exists():
            messagebox.showwarning(APP_NAME, "Fichier introuvable :\n%s" % self.output, parent=self)
            return
        # Les lecteurs PDF des navigateurs comprennent l'ancre #page=N
        if not webbrowser.open(self.output.as_uri() + "#page=%d" % page):
            os.startfile(str(self.output))

    def _export(self):
        f = filedialog.asksaveasfilename(parent=self, title="Exporter les phrases à vérifier", defaultextension=".csv",
                                         initialdir=str(self.output.parent),
                                         initialfile=self.output.stem + "_a_verifier.csv", filetypes=[("CSV", "*.csv")])
        if not f:
            return
        with open(f, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["N°", "Statut", "Emplacement (traduction)", "Emplacement (original)", "Autres emplacements",
                        "Motifs", "Original", "Traduction", "Note"])
            for r in self.rows:
                loc = r["locations"][0]
                w.writerow([r["id"], "Vérifiée" if r.get("checked") else "À vérifier", loc["tgt_label"], loc["src_label"],
                            " | ".join(l["tgt_label"] for l in r["locations"][1:]), " | ".join(r["reasons"]),
                            r["src"], r["tgt"], r.get("note", "")])
        messagebox.showinfo(APP_NAME, "Export enregistré :\n%s" % f, parent=self)
