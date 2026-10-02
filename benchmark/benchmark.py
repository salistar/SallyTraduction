#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Banc d'essai de traduction EN -> FR sur un extrait du PDF de test.

    python benchmark.py opus     # Opus-MT + CTranslate2 int8 (processeur)
    python benchmark.py qwen     # Qwen3-30B-A3B-Instruct-2507 via Ollama
    python benchmark.py hunyuan  # Hunyuan-MT-7B via Ollama

Options : --first 11 --pages 20 (pages du PDF à traduire).
Résultats écrits dans le dossier du modèle : traduction_FR.txt et RESULTAT.md.
"""
import argparse
import json
import os
import re
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(ROOT, "00-Document-Test", "Helios_Operations_Manual_EN_500p.pdf")
TOTAL_WORDS_500P = 204417          # mots du document complet (sortie du générateur)
OLLAMA = "http://127.0.0.1:11434/api/chat"

ENGINES = {
    "opus": dict(folder="03-Opus-MT-CTranslate2-OpenVINO", label="Opus-MT en-fr (CTranslate2 int8, CPU)"),
    "qwen": dict(folder="01-Qwen3-30B-A3B-Instruct-2507", label="Qwen3-30B-A3B-Instruct-2507 (UD-Q3_K_XL, Ollama)",
                 model="hf.co/unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:UD-Q3_K_XL",
                 options=dict(temperature=0.3, top_p=0.8, top_k=20, num_ctx=4096)),
    "hunyuan": dict(folder="02-Hunyuan-MT-7B", label="Hunyuan-MT-7B (Q4_K_M, Ollama)",
                    model="hf.co/mradermacher/Hunyuan-MT-7B-GGUF:Q4_K_M",
                    # Réglages recommandés par Tencent
                    options=dict(temperature=0.7, top_p=0.6, top_k=20, repeat_penalty=1.05, num_ctx=4096)),
}

PROMPT = ("Translate the following segment into French, without additional explanation. "
          "Keep code, commands, file names and product names unchanged.\n\n{text}")

HEADER_RX = re.compile(r"^(Helios Platform - Operations Reference Manual.*|Page \d+ of \d+.*|Version 4\.2.*)$")


def extract(first, n):
    from pypdf import PdfReader
    reader = PdfReader(PDF)
    lines = []
    for p in range(first - 1, first - 1 + n):
        for ln in reader.pages[p].extract_text().splitlines():
            ln = ln.strip()
            if ln and not HEADER_RX.match(ln):
                lines.append(ln)
    return lines


def chunks(lines, max_words=220):
    """Regroupe les lignes en segments d'environ max_words mots (coupure en fin de ligne)."""
    out, cur, words = [], [], 0
    for ln in lines:
        cur.append(ln)
        words += len(ln.split())
        if words >= max_words and re.search(r"[.:;]$", ln):
            out.append("\n".join(cur))
            cur, words = [], 0
    if cur:
        out.append("\n".join(cur))
    return out


def run_opus(segments, folder):
    import ctranslate2
    import sentencepiece as spm
    mdir = os.path.join(folder, "opus-mt-en-fr-ct2")
    sp_src = spm.SentencePieceProcessor(model_file=os.path.join(mdir, "source.spm"))
    sp_tgt = spm.SentencePieceProcessor(model_file=os.path.join(mdir, "target.spm"))
    tr = ctranslate2.Translator(mdir, device="cpu", compute_type="int8", inter_threads=4, intra_threads=4)
    sents, seg_of = [], []
    for i, seg in enumerate(segments):
        text = " ".join(seg.split("\n"))
        for s in re.split(r"(?<=[.!?:;])\s+", text):
            if s.strip():
                sents.append(s)
                seg_of.append(i)
    t0 = time.time()
    src = [sp_src.encode(s, out_type=str) + ["</s>"] for s in sents]
    res = tr.translate_batch(src, max_batch_size=32, beam_size=2)
    outs = [sp_tgt.decode([p for p in r.hypotheses[0] if p != "</s>"]) for r in res]
    dt = time.time() - t0
    out_tokens = sum(len(r.hypotheses[0]) for r in res)
    paras = [[] for _ in segments]
    for i, o in zip(seg_of, outs):
        paras[i].append(o)
    return "\n\n".join(" ".join(p) for p in paras), dt, dict(out_tokens=out_tokens, in_tokens=sum(len(s) for s in src),
                                                              note="%d phrases traduites par lots de 32" % len(sents))


def run_ollama(segments, cfg):
    outs, t_total = [], 0.0
    ev_n = ev_d = pe_n = pe_d = 0
    # Chargement du modèle (non compté dans la mesure)
    t0 = time.time()
    call(cfg, "Hello.")
    load = time.time() - t0
    for i, seg in enumerate(segments, 1):
        t0 = time.time()
        r = call(cfg, seg)
        t_total += time.time() - t0
        outs.append(r["message"]["content"].strip())
        ev_n += r.get("eval_count", 0); ev_d += r.get("eval_duration", 0)
        pe_n += r.get("prompt_eval_count", 0); pe_d += r.get("prompt_eval_duration", 0)
        print("  segment %d/%d  %.0f s  %.1f tok/s" % (i, len(segments), time.time() - t0,
              r.get("eval_count", 0) / max(r.get("eval_duration", 1) / 1e9, 1e-9)), flush=True)
    return "\n\n".join(outs), t_total, dict(out_tokens=ev_n, gen_tps=ev_n / max(ev_d / 1e9, 1e-9),
                                            in_tokens=pe_n, prompt_tps=pe_n / max(pe_d / 1e9, 1e-9),
                                            note="chargement du modèle : %.0f s (non compté)" % load)


def call(cfg, text):
    body = json.dumps(dict(model=cfg["model"], stream=False, keep_alive="10m", options=cfg["options"],
                           messages=[dict(role="user", content=PROMPT.format(text=text))])).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as f:
        return json.load(f)


def hms(sec):
    sec = int(round(sec))
    h, m = divmod(sec, 3600)
    m, s = divmod(m, 60)
    return ("%d h %02d min" % (h, m)) if h else ("%d min %02d s" % (m, s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", choices=ENGINES)
    ap.add_argument("--first", type=int, default=11)
    ap.add_argument("--pages", type=int, default=20)
    a = ap.parse_args()
    cfg = ENGINES[a.engine]
    folder = os.path.join(ROOT, cfg["folder"])

    lines = extract(a.first, a.pages)
    segments = chunks(lines)
    words = sum(len(s.split()) for s in segments)
    print("%s : %d pages, %d mots, %d segments" % (cfg["label"], a.pages, words, len(segments)), flush=True)

    if a.engine == "opus":
        text, dt, st = run_opus(segments, folder)
    else:
        text, dt, st = run_ollama(segments, cfg)

    factor = TOTAL_WORDS_500P / words
    est = dt * factor
    with open(os.path.join(folder, "source_EN.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(segments))
    with open(os.path.join(folder, "traduction_FR.txt"), "w", encoding="utf-8") as f:
        f.write(text)

    rows = [("Extrait traduit", "pages %d à %d (%d mots, %d segments)" % (a.first, a.first + a.pages - 1, words, len(segments))),
            ("Durée mesurée", hms(dt)),
            ("Vitesse", "%.0f mots/min" % (words / dt * 60)),
            ("Tokens produits", "%d" % st["out_tokens"])]
    if "gen_tps" in st:
        rows += [("Génération", "%.1f tokens/s" % st["gen_tps"]),
                 ("Lecture du texte source", "%.0f tokens/s" % st["prompt_tps"])]
    rows += [("**Projection 500 pages (traduction seule)**", "**%s**" % hms(est)),
             ("Remarque", st["note"])]
    md = ["# Résultat du test : %s" % cfg["label"], "",
          "Date : %s" % time.strftime("%d/%m/%Y %H:%M"), "", "| Mesure | Valeur |", "|---|---|"]
    md += ["| %s | %s |" % r for r in rows]
    md += ["", "Projection = durée mesurée × (204 417 mots du document complet / mots de l'extrait).",
           "Ne comprend pas l'extraction ni la reconstruction de la mise en page du PDF.", "",
           "Fichiers : `source_EN.txt` (texte d'origine) et `traduction_FR.txt` (traduction à relire)."]
    with open(os.path.join(folder, "RESULTAT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join("%s : %s" % (k.strip("*"), v.strip("*")) for k, v in rows))


if __name__ == "__main__":
    main()
