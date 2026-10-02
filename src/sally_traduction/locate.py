"""Emplacement exact d'une phrase : page, ligne (comptée depuis le haut de la page) et position du mot.

PDF  : lignes visuelles reconstituées à partir des coordonnées des mots (en-têtes et pieds de page compris).
Word : la pagination dépend de l'affichage de Word ; on donne la partie (corps, en-tête…), le numéro de
       paragraphe et la position du mot dans le paragraphe.
"""
import re

_WORD = re.compile(r"[^\w]+", re.UNICODE)


def norm(w):
    return _WORD.sub("", w.lower())


def tokens(text):
    return [t for t in (norm(x) for x in text.split()) if t]


class PdfLocator:
    def __init__(self, path):
        import pymupdf
        self.doc = pymupdf.open(path)
        self.cache = {}

    def close(self):
        self.doc.close()

    def _page(self, pno):
        """Mots de la page dans l'ordre de lecture, avec (ligne visuelle, position dans la ligne)."""
        if pno in self.cache:
            return self.cache[pno]
        words = self.doc[pno - 1].get_text("words")          # x0, y0, x1, y1, mot, bloc, ligne, n°
        if not words:
            self.cache[pno] = []
            return []
        by_y = sorted(range(len(words)), key=lambda i: (words[i][1] + words[i][3]) / 2)
        lines, cur, cur_y, cur_h = [], [], None, None
        for i in by_y:
            w = words[i]
            yc, h = (w[1] + w[3]) / 2, max(1.0, w[3] - w[1])
            if cur and abs(yc - cur_y) <= 0.45 * max(h, cur_h):
                cur.append(i)
            else:
                if cur:
                    lines.append(cur)
                cur, cur_y, cur_h = [i], yc, h
        if cur:
            lines.append(cur)
        pos = {}
        for li, idx in enumerate(lines, 1):
            for wi, i in enumerate(sorted(idx, key=lambda i: words[i][0]), 1):
                pos[i] = (li, wi)
        seq = [(norm(w[4]), pos[i][0], pos[i][1]) for i, w in enumerate(words) if norm(w[4])]
        self.cache[pno] = seq
        return seq

    def find(self, pno, sentence, start_hint=0):
        """Renvoie (ligne, mot) du premier mot de la phrase sur la page, ou None."""
        toks = tokens(sentence)
        if not toks or not pno:
            return None
        seq = self._page(pno)
        for k in (min(6, len(toks)), 3, 2, 1):
            if k > len(toks) or (k == 1 and len(toks[0]) < 5):
                continue
            want = toks[:k]
            hits = [i for i in range(len(seq) - k + 1) if all(seq[i + j][0] == want[j] for j in range(k))]
            if hits:
                i = min(hits, key=lambda h: abs(h - start_hint)) if start_hint else hits[0]
                return seq[i][1], seq[i][2]
        return None


def word_offset(sentences, k, prefix=""):
    """Position (1-based) du premier mot de la k-ième phrase dans le paragraphe reconstitué."""
    return len(prefix.split()) + sum(len(s.split()) for s in sentences[:k]) + 1


def label(loc):
    """Texte lisible d'un emplacement."""
    if not loc:
        return ""
    if loc.get("page"):
        s = "Page %d" % loc["page"]
        if loc.get("line"):
            s += " · ligne %d · mot %d" % (loc["line"], loc["word"])
        else:
            s += " · emplacement exact non retrouvé"
        return s
    return "%s · paragraphe %d · mot %d" % (loc.get("part", "Corps"), loc.get("para", 0), loc.get("word", 0))
