"""Moteurs locaux : traduction (Opus-MT, M2M-100), détection de langue, similarité sémantique."""
import os
import re

import numpy as np

from .paths import model_path

THREADS = max(1, os.cpu_count() or 4)
CHUNK = 1024


class Cancelled(Exception):
    pass


def _check(cancel):
    if cancel is not None and cancel.is_set():
        raise Cancelled()


# --------------------------------------------------------------------------
# Découpage en phrases
# --------------------------------------------------------------------------
_ABBR = {"e.g.", "i.e.", "etc.", "vs.", "mr.", "mrs.", "dr.", "fig.", "no.", "p.", "pp.", "approx.", "cf.",
         "env.", "ex.", "m.", "mme.", "art.", "vol.", "inc.", "ltd.", "jr.", "sr.", "st."}
_SPLIT_RX = re.compile(r"(?<=[.!?:;])\s+(?=[\"'«(\[A-Z0-9ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸ])")


def split_sentences(text: str):
    text = " ".join(text.split())
    if not text:
        return []
    parts = _SPLIT_RX.split(text)
    out = []
    for p in parts:
        if out and out[-1].split()[-1].lower() in _ABBR:
            out[-1] += " " + p
        else:
            out.append(p)
    return out


# --------------------------------------------------------------------------
# Traduction
# --------------------------------------------------------------------------
class _CT2Base:
    def _translator(self, path, beam):
        import ctranslate2
        inter = max(1, min(8, THREADS // 2))
        self.beam = beam
        self.tr = ctranslate2.Translator(str(path), device="cpu", compute_type="int8",
                                         inter_threads=inter, intra_threads=2 if THREADS >= 4 else 1)

    def _run(self, sentences, encode, decode, progress=None, cancel=None, prefix=None):
        out = [""] * len(sentences)
        idx = [i for i, s in enumerate(sentences) if s.strip()]
        for k in range(0, len(idx), CHUNK):
            _check(cancel)
            part = idx[k:k + CHUNK]
            kw = {"target_prefix": [prefix] * len(part)} if prefix else {}
            res = self.tr.translate_batch([encode(sentences[i]) for i in part], max_batch_size=32,
                                          beam_size=self.beam, max_decoding_length=512, **kw)
            for i, r in zip(part, res):
                out[i] = decode(r.hypotheses[0])
            if progress:
                progress(min(1.0, (k + len(part)) / max(1, len(idx))))
        return out


class OpusTranslator(_CT2Base):
    """Opus-MT (Helsinki-NLP) converti en CTranslate2 int8 ; key = 'opus-en-fr' ou 'opus-fr-en'."""

    def __init__(self, key):
        import sentencepiece as spm
        path = model_path(key)
        self.sp_src = spm.SentencePieceProcessor(model_file=str(path / "source.spm"))
        self.sp_tgt = spm.SentencePieceProcessor(model_file=str(path / "target.spm"))
        self._translator(path, beam=2)

    def translate(self, sentences, progress=None, cancel=None):
        return self._run(sentences,
                         lambda s: self.sp_src.encode(s, out_type=str)[:400] + ["</s>"],
                         lambda h: self.sp_tgt.decode([p for p in h if p != "</s>"]),
                         progress, cancel)


class M2MTranslator(_CT2Base):
    """M2M-100 418M (Meta, licence MIT) : second traducteur indépendant pour le contre-avis."""

    def __init__(self):
        import sentencepiece as spm
        path = model_path("m2m100")
        self.sp = spm.SentencePieceProcessor(model_file=str(path / "sentencepiece.bpe.model"))
        self._translator(path, beam=1)

    def translate(self, sentences, src, tgt, progress=None, cancel=None):
        return self._run(sentences,
                         lambda s: ["__%s__" % src] + self.sp.encode(s, out_type=str)[:400] + ["</s>"],
                         lambda h: self.sp.decode([p for p in h[1:] if p != "</s>"]),
                         progress, cancel, prefix=["__%s__" % tgt])


# --------------------------------------------------------------------------
# Détection de langue (fastText lid.176)
# --------------------------------------------------------------------------
_EN_WORDS = set("the of and to in is that for it with as be on are this by from or at an not which can must "
                "should will was were has have been if when then before after all each any into than only also "
                "these those their there what your you we they its do does".split())
_FR_WORDS = set("le la les de des du et est que qui pour dans un une en sur par ne pas au aux avec ce cette ces "
                "doit sont être peut il elle ils se sa son ses leur leurs mais ou où donc car si lors après avant "
                "tous toutes chaque plus comme été fait vous nous".split())
_ACCENTS = re.compile(r"[àâçéèêëîïôùûüœ]")
_WORD_RX = re.compile(r"[a-zàâäçéèêëîïôöùûüÿœ]+")


def simple_detect(text):
    """Détecteur anglais / français intégré (mots fréquents + accents), utilisé si fastText est indisponible."""
    low = text.lower()
    words = _WORD_RX.findall(low)
    en = sum(w in _EN_WORDS for w in words)
    fr = sum(w in _FR_WORDS for w in words) + 0.5 * len(_ACCENTS.findall(low))
    total = en + fr
    if total < 1:
        return ("?", 0.0)
    return ("fr", fr / total) if fr > en else ("en", en / total)


def fasttext_available():
    try:
        import fasttext  # noqa: F401
        return (model_path("lid") / "lid.176.ftz").exists()
    except Exception:
        return False


class LangID:
    """fastText lid.176 si disponible (Python ≤ 3.12), sinon détecteur anglais / français intégré."""

    def __init__(self):
        self.m = None
        self.backend = "intégré (anglais / français)"
        if fasttext_available():
            try:
                import fasttext
                fasttext.FastText.eprint = lambda *a, **k: None
                self.m = fasttext.load_model(str(model_path("lid") / "lid.176.ftz"))
                self.backend = "fastText lid.176"
            except Exception:
                self.m = None

    def detect(self, texts):
        if not texts:
            return []
        if self.m is None:
            return [simple_detect(t) for t in texts]
        labels, probs = self.m.predict([" ".join(t.split()) for t in texts], k=1)
        return [(l[0].replace("__label__", "") if l else "?", float(p[0]) if len(p) else 0.0)
                for l, p in zip(labels, probs)]


# --------------------------------------------------------------------------
# Similarité sémantique multilingue (MiniLM ONNX int8)
# --------------------------------------------------------------------------
class Embedder:
    def __init__(self):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        path = model_path("minilm")
        self.tok = Tokenizer.from_file(str(path / "tokenizer.json"))
        self.tok.enable_truncation(128)
        pad = self.tok.token_to_id("<pad>")
        self.tok.enable_padding(pad_id=pad if pad is not None else 1, pad_token="<pad>")
        so = ort.SessionOptions()
        so.intra_op_num_threads = min(8, THREADS)
        so.log_severity_level = 3
        self.sess = ort.InferenceSession(str(path / "model_quint8_avx2.onnx"), so, providers=["CPUExecutionProvider"])
        self.inputs = [i.name for i in self.sess.get_inputs()]

    def encode(self, texts, progress=None, cancel=None, batch=32):
        out = np.zeros((len(texts), 384), dtype=np.float32)
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        for k in range(0, len(order), batch):
            _check(cancel)
            ids = order[k:k + batch]
            enc = self.tok.encode_batch([texts[i] or " " for i in ids])
            feeds = {"input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                     "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64)}
            if "token_type_ids" in self.inputs:
                feeds["token_type_ids"] = np.zeros_like(feeds["input_ids"])
            hidden = self.sess.run(None, {n: feeds[n] for n in self.inputs})[0]
            mask = feeds["attention_mask"][..., None].astype(np.float32)
            vec = (hidden * mask).sum(1) / np.clip(mask.sum(1), 1e-9, None)
            vec /= np.clip(np.linalg.norm(vec, axis=1, keepdims=True), 1e-9, None)
            out[ids] = vec
            if progress:
                progress(min(1.0, (k + len(ids)) / max(1, len(order))))
        return out


def cosine_rows(a, b):
    return np.sum(a * b, axis=1)
