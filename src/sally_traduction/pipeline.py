"""Chaîne complète : lecture -> traduction -> vérifications -> reconstruction -> rapport."""
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import engines, protect
from .documents import open_document
from .paths import model_available

LANG_NAMES = {"en": "anglais", "fr": "français"}

# Seuils de contrôle (similarité cosinus MiniLM, 0 à 1)
TH_CROSS = 0.62      # phrase source <-> traduction (multilingue)
TH_BACK = 0.70       # phrase source <-> retraduction
TH_SECOND = 0.66     # traduction Opus <-> traduction M2M-100 (si confirmé par un autre contrôle)
TH_SECOND_STRONG = 0.50
TH_LANG = 0.50       # confiance fastText dans la langue cible

STAGES = [("analyse", "Analyse du document"), ("traduction", "Traduction"),
          ("verification", "Vérifications"), ("reconstruction", "Reconstruction du fichier"),
          ("rapport", "Rapport de contrôle")]

NUM_RX = re.compile(r"\d+(?:[.,\s  ]\d+)*")
TOKEN_RX = re.compile(r"(?:https?://\S+|[\w-]+(?:[./_=:][\w-]+){1,}|`[^`]+`)")


@dataclass
class Options:
    direction: str = "auto"          # 'auto', 'en-fr' ou 'fr-en'
    backtranslation: bool = True
    semantic: bool = True
    second_opinion: bool = True
    overrides: dict = None           # {phrase source: traduction imposée} (relecture par LLM)
    out_suffix: str = ""             # ajouté au nom du fichier produit (ex. « _LLM »)


@dataclass
class Result:
    output: Path = None
    report: Path = None
    review: Path = None
    direction: str = ""
    segments: int = 0
    sentences: int = 0
    flagged: int = 0
    coverage: float = 0.0
    lang_ok: float = 0.0
    numbers_ok: float = 0.0
    confidence: float = 0.0
    duration: float = 0.0
    pages: int = 0
    timings: dict = field(default_factory=dict)


def _numbers(s):
    return sorted(re.sub(r"\D", "", m) for m in NUM_RX.findall(s))


def _tokens(s):
    return {t.strip("`.,;:") for t in TOKEN_RX.findall(s) if len(t) >= 5 and not re.fullmatch(r"[\d.,:]+", t)}


def run(input_path, out_dir, opts: Options, progress=None, log=None, cancel=None):
    """progress(stage_key, fraction, message) ; log(message)."""
    t_start = time.time()
    input_path, out_dir = Path(input_path).resolve(), Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    say = log or (lambda m: None)
    prog = progress or (lambda *a: None)
    res = Result()
    timings = {}

    def stage(key):
        timings[key] = time.time()

    def done(key):
        timings[key] = time.time() - timings[key]

    # 1. Analyse ------------------------------------------------------------
    stage("analyse")
    prog("analyse", 0.05, "Lecture de %s" % input_path.name)
    doc = open_document(input_path)
    segs = doc.segments
    if not segs:
        raise ValueError("Aucun texte à traduire n'a été trouvé (PDF scanné ? une reconnaissance OCR est nécessaire).")
    res.pages = doc.page_count
    say("%d blocs de texte détectés%s." % (len(segs), (" sur %d pages" % res.pages) if res.pages else ""))
    if getattr(doc, "scanned_pages", 0):
        say("Attention : %d page(s) sans texte (scannées ?) ne seront pas traduites." % doc.scanned_pages)

    lid = engines.LangID()
    say("Détection de langue : %s." % lid.backend)
    direction = opts.direction
    if direction == "auto":
        sample = [s.text for s in segs[:400] if len(s.text.split()) >= 4][:200] or [s.text for s in segs[:50]]
        votes = {}
        for lang, p in lid.detect(sample):
            votes[lang] = votes.get(lang, 0) + p
        src = "fr" if votes.get("fr", 0) > votes.get("en", 0) else "en"
        direction = "%s-%s" % (src, "en" if src == "fr" else "fr")
        say("Langue détectée : %s." % LANG_NAMES[src])
    src_lang, tgt_lang = direction.split("-")
    res.direction = direction

    # Phrases uniques (les en-têtes répétés ne sont traduits qu'une fois)
    seg_sents = [engines.split_sentences(s.text) for s in segs]
    uniq, index = [], {}
    for sents in seg_sents:
        for s in sents:
            if s not in index:
                index[s] = len(uniq)
                uniq.append(s)
    res.segments, res.sentences = len(segs), sum(len(x) for x in seg_sents)
    say("%d phrases (%d uniques) à traduire de l'%s vers le %s." % (res.sentences, len(uniq),
        LANG_NAMES[src_lang], LANG_NAMES[tgt_lang]))
    prog("analyse", 1.0, "Analyse terminée")
    done("analyse")

    # 2. Traduction ---------------------------------------------------------
    stage("traduction")
    prog("traduction", 0.0, "Chargement d'Opus-MT %s" % direction)
    glossary = protect.load_glossary(direction)
    masked = [protect.protect(s, glossary) for s in uniq]
    n_prot = sum(len(v) for _, v in masked)
    say("%d terme(s) technique(s) ou de glossaire protégé(s) (%s)." % (n_prot, protect.glossary_path()))
    opus = engines.OpusTranslator("opus-%s" % direction)
    raw = opus.translate([m for m, _ in masked], lambda f: prog("traduction", f, "Traduction des phrases"), cancel)
    tgt, lost = [], []
    for t, (_, vals) in zip(raw, masked):
        txt, miss = protect.restore(t, vals, tgt_lang)
        tgt.append(txt)
        lost.append(miss)
    if opts.overrides:                       # traductions corrigées (relecture par LLM)
        n_over = 0
        for i, s in enumerate(uniq):
            if s in opts.overrides and opts.overrides[s].strip():
                tgt[i] = opts.overrides[s].strip()
                lost[i] = 0
                n_over += 1
        say("%d phrase(s) remplacée(s) par la relecture du LLM." % n_over)
    done("traduction")
    say("Traduction terminée en %.0f s." % timings["traduction"])

    # 3. Vérifications ------------------------------------------------------
    stage("verification")
    n = len(uniq)
    checks = [dict(reasons=[], scores={}) for _ in range(n)]
    weights = {"regles": 0.1, "retraduction": 0.3, "semantique": 0.2, "second": 0.4}
    active = ["regles"] + [k for k, on in (("retraduction", opts.backtranslation), ("semantique", opts.semantic),
                                           ("second", opts.second_opinion and model_available("m2m100"))) if on]
    wsum = sum(weights[k] for k in active)
    base = 0.0

    def sub(key, label):
        w = weights[key] / wsum
        def f(x):
            prog("verification", base + w * x, label)
        return f, w

    # 3a. Règles : vide, non traduit, langue, nombres, éléments techniques
    f, w = sub("regles", "Contrôle de la langue, des nombres et du code")
    langs = lid.detect(tgt)
    # mots réellement traduisibles (hors code, chemins, termes protégés)
    free = [len(re.findall(r"[A-Za-zÀ-ÿ]{2,}", protect.MARK_RX.sub(" ", m))) for m, _ in masked]
    lang_ok = num_ok = cov_ok = 0
    for i, (s, t) in enumerate(zip(uniq, tgt)):
        c = checks[i]
        if not t.strip():
            c["reasons"].append("Traduction vide")
        elif free[i] >= 3 and t.strip() == s.strip():
            c["reasons"].append("Phrase non traduite")
        else:
            cov_ok += 1
        lang, p = langs[i]
        c["scores"]["langue"] = round(p if lang == tgt_lang else 0.0, 3)
        wrong = (lang == src_lang and p >= TH_LANG) or (lang not in (src_lang, tgt_lang) and p >= 0.8)
        if free[i] >= 6 and wrong:
            c["reasons"].append("Langue détectée : %s" % lang)
        else:
            lang_ok += 1
        if _numbers(s) != _numbers(t):
            c["reasons"].append("Nombres différents")
        else:
            num_ok += 1
        missing = [k for k in _tokens(s) if k not in t]
        if missing:
            c["reasons"].append("Élément technique modifié : %s" % ", ".join(sorted(missing)[:3]))
        if lost[i]:
            c["reasons"].append("Terme protégé perdu (%d)" % lost[i])
        if i % 500 == 0:
            f(i / n)
    f(1.0)
    base += w
    res.coverage, res.lang_ok, res.numbers_ok = cov_ok / n, lang_ok / n, num_ok / n

    emb = engines.Embedder() if ("semantique" in active or "retraduction" in active or "second" in active) else None
    e_src = e_tgt = None
    cross = bsim = None
    sims = []

    # 3b. Similarité source <-> traduction
    if "semantique" in active:
        f, w = sub("semantique", "Similarité sémantique source / traduction")
        e_src = emb.encode(uniq, lambda x: f(0.5 * x), cancel)
        e_tgt = emb.encode(tgt, lambda x: f(0.5 + 0.5 * x), cancel)
        cross = engines.cosine_rows(e_src, e_tgt)
        sims.append(cross)
        for i, v in enumerate(cross):
            checks[i]["scores"]["semantique"] = round(float(v), 3)
            if v < TH_CROSS and free[i] >= 3:
                checks[i]["reasons"].append("Sens éloigné de la source (%.2f)" % v)
        base += w

    # 3c. Retraduction
    if "retraduction" in active:
        f, w = sub("retraduction", "Retraduction vers la langue d'origine")
        back_tr = engines.OpusTranslator("opus-%s-%s" % (tgt_lang, src_lang))
        back = back_tr.translate(tgt, lambda x: f(0.7 * x), cancel)
        if e_src is None:
            e_src = emb.encode(uniq, lambda x: f(0.7 + 0.15 * x), cancel)
        e_back = emb.encode(back, lambda x: f(0.85 + 0.15 * x), cancel)
        bsim = engines.cosine_rows(e_src, e_back)
        sims.append(bsim)
        for i, v in enumerate(bsim):
            checks[i]["scores"]["retraduction"] = round(float(v), 3)
            checks[i]["back"] = back[i]
            if v < TH_BACK and free[i] >= 3:
                checks[i]["reasons"].append("Retraduction divergente (%.2f)" % v)
        base += w

    # 3d. Deuxième avis M2M-100
    if "second" in active:
        f, w = sub("second", "Deuxième avis (M2M-100)")
        m2m = engines.M2MTranslator()
        alt_raw = m2m.translate([m for m, _ in masked], src_lang, tgt_lang, lambda x: f(0.8 * x), cancel)
        alt = [protect.restore(t, vals, tgt_lang)[0] for t, (_, vals) in zip(alt_raw, masked)]
        if e_tgt is None:
            e_tgt = emb.encode(tgt, lambda x: f(0.8 + 0.1 * x), cancel)
        e_alt = emb.encode(alt, lambda x: f(0.9 + 0.1 * x), cancel)
        asim = engines.cosine_rows(e_tgt, e_alt)
        sims.append(asim)
        for i, v in enumerate(asim):
            checks[i]["scores"]["second_avis"] = round(float(v), 3)
            checks[i]["alt"] = alt[i]
            # M2M-100 est moins précis qu'Opus : son désaccord ne compte que s'il est fort,
            # ou s'il est confirmé par un autre contrôle
            others = [x[i] for x in (cross, bsim) if x is not None]
            weak = others and min(others) < 0.78
            if free[i] >= 3 and (v < TH_SECOND_STRONG or (v < TH_SECOND and weak)):
                checks[i]["reasons"].append("Désaccord avec le second traducteur (%.2f)" % v)
        base += w

    conf = np.mean(np.vstack(sims), axis=0) if sims else np.ones(n)
    for i in range(n):
        checks[i]["confidence"] = float(conf[i])
    done("verification")
    prog("verification", 1.0, "Vérifications terminées")

    # 4. Reconstruction -----------------------------------------------------
    stage("reconstruction")
    translations = {}
    for seg, sents in zip(segs, seg_sents):
        translations[seg.id] = " ".join(tgt[index[s]] for s in sents)
    doc.apply(translations, lambda x: prog("reconstruction", 0.95 * x, "Écriture du document traduit"), cancel)
    suffix = "_" + tgt_lang.upper() + (opts.out_suffix or "")
    out = out_dir / (input_path.stem + suffix + input_path.suffix.lower())
    k = 2
    while out.exists():
        out = out_dir / ("%s%s (%d)%s" % (input_path.stem, suffix, k, input_path.suffix.lower()))
        k += 1
    doc.save(out)
    res.output = out
    prog("reconstruction", 1.0, "Document enregistré")
    done("reconstruction")

    # 5. Rapport ------------------------------------------------------------
    stage("rapport")
    prog("rapport", 0.1, "Localisation des phrases à vérifier")
    flagged_ids = {i for i in range(n) if checks[i]["reasons"]}
    res.flagged = sum(1 for sents in seg_sents for s in sents if index[s] in flagged_ids)
    res.confidence = float(np.mean(conf)) if n else 0.0
    from . import locate
    loc_src = loc_tgt = None
    if doc.kind == "pdf":
        loc_src, loc_tgt = locate.PdfLocator(input_path), locate.PdfLocator(out)
    rows, by_sentence = [], {}
    for seg, sents in zip(segs, seg_sents):
        tsents = [tgt[index[s]] for s in sents]
        for k, s in enumerate(sents):
            i = index[s]
            if i not in flagged_ids:
                continue
            if doc.kind == "pdf":
                a = loc_src.find(seg.page, s)
                b = loc_tgt.find(seg.page, tgt[i])
                src_loc = dict(page=seg.page, line=a[0] if a else 0, word=a[1] if a else 0)
                tgt_loc = dict(page=seg.page, line=b[0] if b else 0, word=b[1] if b else 0)
            else:
                part, para = seg.meta.get("part", "Corps"), seg.meta.get("para", 0)
                src_loc = dict(part=part, para=para, word=locate.word_offset(sents, k, seg.prefix))
                tgt_loc = dict(part=part, para=para, word=locate.word_offset(tsents, k, seg.prefix))
            occ = dict(src=src_loc, tgt=tgt_loc, src_label=locate.label(src_loc), tgt_label=locate.label(tgt_loc))
            if i in by_sentence:
                by_sentence[i]["locations"].append(occ)
                continue
            row = dict(id=len(rows) + 1, page=seg.page, src=s, tgt=tgt[i], back=checks[i].get("back", ""),
                       alt=checks[i].get("alt", ""), reasons=checks[i]["reasons"], scores=checks[i]["scores"],
                       confidence=checks[i]["confidence"], locations=[occ], checked=False, note="")
            by_sentence[i] = row
            rows.append(row)
    for l in (loc_src, loc_tgt):
        if l:
            l.close()
    res.duration = time.time() - t_start
    timings["rapport"] = 0.0
    res.timings = timings
    from .report import write_report, write_review
    res.report = out.with_name(out.stem + "_rapport.html")
    res.review = out.with_name(out.stem + "_verification.json")
    write_review(res.review, input_path, out, res, rows)
    write_report(res.report, input_path, res, rows, active)
    prog("rapport", 1.0, "Rapport enregistré")
    say("Terminé en %.0f s : %d phrase(s) à relire sur %d." % (res.duration, res.flagged, res.sentences))
    return res
