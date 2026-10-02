"""Protection des éléments techniques et glossaire imposé.

Avant traduction, chaque élément protégé est remplacé par un marqueur (ZQX0, ZQX1…) que les
modèles recopient tels quels ; après traduction, le marqueur est remplacé par l'original
(code, commande, chemin) ou par la traduction imposée du glossaire.
"""
import re

from .paths import user_dir

DEFAULT_GLOSSARY = """# Glossaire SallyTraduction
# Une entrée par ligne :   terme anglais = terme français
# Le terme est reconnu sans tenir compte des majuscules ; l'entrée la plus longue est prioritaire.
# Pour garder un terme tel quel dans les deux langues :   pod = pod
# En traduction français -> anglais, le glossaire est utilisé dans l'autre sens.

pod = pod
pods = pods
namespace = namespace
namespaces = namespaces
cluster = cluster
clusters = clusters
node pool = pool de nœuds
node pools = pools de nœuds
service mesh control plane = plan de contrôle du service mesh
control plane = plan de contrôle
service mesh = service mesh
sidecar = sidecar
load balancer = répartiteur de charge
load balancers = répartiteurs de charge
on-call engineer = ingénieur d'astreinte
on-call engineers = ingénieurs d'astreinte
on-call rotation = rotation d'astreinte
on-call = astreinte
runbook = runbook
runbooks = runbooks
rollback = retour arrière
health check = contrôle de santé
health checks = contrôles de santé
change freeze = gel des changements
blast radius = rayon d'impact
error budget = budget d'erreur
error budgets = budgets d'erreur
merge request = merge request
pull request = pull request
container registry = registre de conteneurs
"""

COMMANDS = ("kubectl", "helm", "docker", "podman", "terraform", "terragrunt", "ansible-playbook", "ansible", "git",
            "systemctl", "journalctl", "curl", "wget", "psql", "pg_dump", "redis-cli", "npm", "pip", "python",
            "ssh", "scp", "grep", "tail", "cat", "sudo", "az", "aws", "gcloud", "vault", "argocd", "flux", "velero")
STOP = {"and", "to", "then", "or", "with", "before", "after", "the", "a", "an", "in", "on", "for", "if", "when",
        "until", "so", "but", "et", "puis", "pour", "avec", "avant", "après", "le", "la", "les", "dans", "sur",
        "si", "quand", "jusqu'à", "ou", "mais"}

_PATTERNS = [
    r"`[^`]+`",                                              # code entre accents graves
    r"https?://[^\s)>\]]+",                                  # URL
    r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",                         # e-mail
    r"(?<![\w-])--?[A-Za-z][\w-]*(?:=[^\s,;)]+)?",           # options de ligne de commande
    r"\b[\w-]*\w(?:[./\\_=:@]\w[\w-]*)+",                    # chemins, domaines, identifiants
    r"\b[a-z]+[A-Z][A-Za-z0-9]*\b|\b[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*\b",  # camelCase / PascalCase
]
TECH_RX = re.compile("|".join("(?:%s)" % p for p in _PATTERNS))
CMD_RX = re.compile(r"\b(?:%s)\b" % "|".join(re.escape(c) for c in sorted(COMMANDS, key=len, reverse=True)))
MARK_RX = re.compile(r"ZQX(\d+)")
_TRAIL = ".,;:!?)"


def glossary_path():
    return user_dir() / "glossaire.txt"


def load_glossary(direction):
    """Renvoie [(motif compilé, remplacement)] pour le sens donné ('en-fr' ou 'fr-en')."""
    path = glossary_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_GLOSSARY, encoding="utf-8")
    pairs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        en, fr = (x.strip() for x in line.split("=", 1))
        if en and fr:
            pairs.append((en, fr) if direction == "en-fr" else (fr, en))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return [(re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(src), re.IGNORECASE), dst) for src, dst in pairs]


def _command_spans(text):
    spans = []
    for m in CMD_RX.finditer(text):
        end = m.end()
        pos = end
        while True:
            nxt = re.match(r"\s+(\S+)", text[pos:])
            if not nxt:
                break
            word = nxt.group(1)
            if word.lower().strip(_TRAIL) in STOP or not re.fullmatch(r"[\w./:=@<>{}\[\]*'\"-]+[.,;:]?", word):
                break
            pos += nxt.end()
            end = pos - (1 if word[-1] in _TRAIL else 0)
            if word[-1] in _TRAIL:
                break
        if end > m.end():                       # seulement si la commande a des arguments
            spans.append((m.start(), end))
    return spans


def protect(text, glossary):
    """Renvoie (texte avec marqueurs, liste des valeurs à réinsérer)."""
    spans = []
    for m in TECH_RX.finditer(text):
        s, e = m.start(), m.end()
        while e > s and text[e - 1] in _TRAIL:
            e -= 1
        if e - s >= 2:
            spans.append((s, e, text[s:e]))
    for s, e in _command_spans(text):
        spans.append((s, e, text[s:e]))
    for rx, dst in glossary:
        for m in rx.finditer(text):
            src = m.group(0)
            plural = src.lower().endswith("s") and dst.lower().endswith(("s", "x"))
            spans.append((m.start(), m.end(), Term(dst, plural)))
    if not spans:
        return text, []
    # garde les plus longs, sans chevauchement
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    kept, last = [], -1
    for s, e, v in spans:
        if s >= last:
            kept.append((s, e, v))
            last = e
    out, values, pos = [], [], 0
    for s, e, v in kept:
        out.append(text[pos:s])
        out.append("ZQX%d" % len(values))
        values.append(v)
        pos = e
    out.append(text[pos:])
    return "".join(out), values


class Term(str):
    """Terme de glossaire : majuscule et article ajustés à la réinsertion."""

    def __new__(cls, value, plural=False):
        obj = super().__new__(cls, value)
        obj.plural = plural
        return obj


_VOWEL = tuple("aeiouyhàâäéèêëîïôöùûü")
_ART_RX = re.compile(r"(?i)\b(le|la)\s+$")


def restore(text, values, tgt_lang="fr"):
    """Réinsère les valeurs ; renvoie (texte, nombre de marqueurs perdus)."""
    if not values:
        return text, 0
    found = set()
    out, pos = [], 0
    for m in MARK_RX.finditer(text):
        i = int(m.group(1))
        before = "".join(out) + text[pos:m.start()]
        if i >= len(values):
            out.append(text[pos:m.end()])
            pos = m.end()
            continue
        found.add(i)
        val = values[i]
        if isinstance(val, Term):
            v = str(val)
            if tgt_lang == "fr":
                a = _ART_RX.search(before)
                if a:
                    art = a.group(1)
                    if val.plural:
                        new = "les " if art.islower() else "Les "
                    elif v.lower().startswith(_VOWEL):
                        new = "l'" if art.islower() else "L'"
                    else:
                        new = None
                    if new:
                        before = before[:a.start()] + new
            start = not before.strip() or before.rstrip()[-1:] in ".!?:"
            v = v[0].upper() + v[1:] if start else (v[0].lower() + v[1:] if v[:1].isupper() and v[1:2].islower() else v)
            out = [before, v]
        else:
            out = [before, str(val)]
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), len(values) - len(found)
