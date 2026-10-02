"""Rapport de contrôle HTML autonome (aucune ressource externe)."""
import html
import json
import time

from . import __version__

LABELS = {"regles": "Langue, nombres, éléments techniques", "semantique": "Similarité sémantique (MiniLM)",
          "retraduction": "Retraduction (Opus-MT inverse)", "second": "Deuxième avis (M2M-100)"}


def _pct(x):
    return "%.1f %%" % (100 * x)


def _dur(s):
    s = int(round(s))
    return "%d min %02d s" % divmod(s, 60) if s >= 60 else "%d s" % s


def write_review(path, source, output, res, rows):
    """Fichier de vérification manuelle (relu et mis à jour par l'application)."""
    data = dict(version=1, source=str(source), output=str(output), kind=output.suffix.lower().lstrip("."),
                direction=res.direction, created=time.strftime("%Y-%m-%d %H:%M"), sentences=res.sentences,
                rows=rows)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def write_report(path, source, res, rows, active):
    ok = res.sentences - res.flagged
    score = ok / res.sentences if res.sentences else 1.0
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    checks = "".join("<li><span class='dot'></span>%s</li>" % LABELS[k] for k in active)
    src_l, tgt_l = res.direction.split("-")
    timings = "".join("<tr><td>%s</td><td>%s</td></tr>" % (k.capitalize(), _dur(v)) for k, v in res.timings.items())
    page = TEMPLATE
    for k, v in {
        "{{TITLE}}": html.escape(source.name),
        "{{DATE}}": time.strftime("%d/%m/%Y à %H:%M"),
        "{{DIR}}": "%s → %s" % (src_l.upper(), tgt_l.upper()),
        "{{SCORE}}": "%.1f" % (100 * score),
        "{{SCORE_DEG}}": "%.1f" % (360 * score),
        "{{OK}}": "{:,}".format(ok).replace(",", " "),
        "{{FLAGGED}}": "{:,}".format(res.flagged).replace(",", " "),
        "{{SENTENCES}}": "{:,}".format(res.sentences).replace(",", " "),
        "{{SEGMENTS}}": "{:,}".format(res.segments).replace(",", " "),
        "{{COVERAGE}}": _pct(res.coverage),
        "{{LANG}}": _pct(res.lang_ok),
        "{{NUMBERS}}": _pct(res.numbers_ok),
        "{{CONF}}": "%.2f" % res.confidence,
        "{{DURATION}}": _dur(res.duration),
        "{{PAGES}}": str(res.pages) if res.pages else "—",
        "{{OUTPUT}}": html.escape(res.output.name),
        "{{CHECKS}}": checks,
        "{{TIMINGS}}": timings,
        "{{VERSION}}": __version__,
        "{{DATA}}": data,
    }.items():
        page = page.replace(k, v)
    path.write_text(page, encoding="utf-8")


TEMPLATE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rapport de traduction</title>
<style>
:root{--bg:#f6f7fb;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--accent:#4f46e5;--accent2:#7c3aed;
--ok:#059669;--warn:#d97706;--bad:#dc2626;--chip:#eef2ff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0b1020;--card:#131a2e;--ink:#e5e9f5;--muted:#94a3b8;
--line:#243049;--accent:#818cf8;--accent2:#a78bfa;--ok:#34d399;--warn:#fbbf24;--bad:#f87171;--chip:#1e2742}}
:root[data-theme="dark"]{--bg:#0b1020;--card:#131a2e;--ink:#e5e9f5;--muted:#94a3b8;--line:#243049;--accent:#818cf8;
--accent2:#a78bfa;--ok:#34d399;--warn:#fbbf24;--bad:#f87171;--chip:#1e2742}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Segoe UI Variable Text","Segoe UI",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:32px 20px 60px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:24px}
.brand{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700}
h1{margin:4px 0 2px;font-size:28px;letter-spacing:-.02em}.sub{color:var(--muted)}
.grid{display:grid;grid-template-columns:300px 1fr;gap:18px}@media(max-width:860px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px}
.ring{width:190px;height:190px;border-radius:50%;margin:6px auto 14px;display:grid;place-items:center;
background:conic-gradient(var(--accent) 0deg,var(--accent2) {{SCORE_DEG}}deg,var(--line) {{SCORE_DEG}}deg)}
.ring>div{width:150px;height:150px;border-radius:50%;background:var(--card);display:grid;place-items:center;text-align:center}
.ring b{font-size:38px;letter-spacing:-.03em}.ring small{display:block;color:var(--muted);font-size:12px;margin-top:-6px}
.center{text-align:center}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}@media(max-width:860px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{background:var(--chip);border-radius:14px;padding:14px 16px}.kpi span{color:var(--muted);font-size:12.5px}.kpi b{display:block;font-size:22px;margin-top:2px}
h2{font-size:16px;margin:0 0 12px}ul.checks{list-style:none;padding:0;margin:0}ul.checks li{padding:6px 0;display:flex;gap:10px;align-items:center}
.dot{width:8px;height:8px;border-radius:50%;background:var(--ok);flex:none}
table.t{width:100%;border-collapse:collapse;font-size:13.5px}table.t td{padding:6px 0;border-bottom:1px solid var(--line)}table.t td+td{text-align:right;color:var(--muted)}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:26px 0 12px}
input,select{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:9px 12px;font:inherit}
input{flex:1;min-width:220px}.count{color:var(--muted);font-size:13px}
.item{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px}
.meta{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}.tag{font-size:12px;padding:2px 9px;border-radius:999px;background:var(--chip);color:var(--accent)}
.tag.w{color:var(--warn)}.tag.b{color:var(--bad)}.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:760px){.pair{grid-template-columns:1fr}}
.lbl{font-size:11.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:2px}
.extra{margin-top:8px;font-size:13px;color:var(--muted)}.empty{text-align:center;color:var(--muted);padding:40px}
.foot{margin-top:30px;color:var(--muted);font-size:12.5px;text-align:center}
.theme{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:10px;padding:8px 12px;cursor:pointer}
</style></head><body><div class="wrap">
<header><div><div class="brand">SallyTraduction · Rapport de contrôle</div><h1>{{TITLE}}</h1>
<div class="sub">{{DIR}} · {{DATE}} · fichier produit : {{OUTPUT}}</div></div>
<button class="theme" onclick="toggleTheme()">Thème clair / sombre</button></header>
<div class="grid"><div class="card center"><h2>Phrases validées automatiquement</h2>
<div class="ring"><div><div><b>{{SCORE}}%</b><small>{{OK}} / {{SENTENCES}}</small></div></div></div>
<div class="sub">{{FLAGGED}} phrase(s) signalée(s) pour relecture</div></div>
<div class="card"><div class="kpis">
<div class="kpi"><span>Couverture</span><b>{{COVERAGE}}</b></div><div class="kpi"><span>Langue cible</span><b>{{LANG}}</b></div>
<div class="kpi"><span>Nombres conservés</span><b>{{NUMBERS}}</b></div><div class="kpi"><span>Similarité moyenne</span><b>{{CONF}}</b></div>
<div class="kpi"><span>Pages</span><b>{{PAGES}}</b></div><div class="kpi"><span>Blocs de texte</span><b>{{SEGMENTS}}</b></div>
<div class="kpi"><span>Phrases</span><b>{{SENTENCES}}</b></div><div class="kpi"><span>Durée totale</span><b>{{DURATION}}</b></div></div>
<div class="pair" style="margin-top:18px"><div><h2>Contrôles appliqués</h2><ul class="checks">{{CHECKS}}</ul></div>
<div><h2>Durée par étape</h2><table class="t">{{TIMINGS}}</table></div></div></div></div>
<div class="toolbar"><input id="q" placeholder="Rechercher dans les phrases signalées…" oninput="render()">
<select id="r" onchange="render()"><option value="">Tous les motifs</option></select><span class="count" id="c"></span></div>
<div id="list"></div>
<div class="foot">Généré localement par SallyTraduction {{VERSION}} — aucune donnée n'a quitté cet ordinateur.</div></div>
<script>
const rows={{DATA}};
const esc=s=>(s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const kinds=[...new Set(rows.flatMap(r=>r.reasons.map(x=>x.replace(/ \(.*|:.*$/,""))))];
const sel=document.getElementById("r");kinds.forEach(k=>{const o=document.createElement("option");o.value=k;o.textContent=k;sel.appendChild(o)});
function render(){const q=document.getElementById("q").value.toLowerCase(),k=sel.value;
const f=rows.filter(r=>(!k||r.reasons.some(x=>x.startsWith(k)))&&(!q||(r.src+" "+r.tgt).toLowerCase().includes(q)));
document.getElementById("c").textContent=f.length+" / "+rows.length+" phrase(s)";
const shown=f.slice(0,800);
document.getElementById("list").innerHTML=shown.length?shown.map(r=>`<div class="item"><div class="meta">${r.locations&&r.locations[0]?`<span class="tag">${esc(r.locations[0].tgt_label)}</span>${r.locations.length>1?`<span class="tag">+${r.locations.length-1} autre(s) emplacement(s)</span>`:""}`:""}
${r.reasons.map(x=>`<span class="tag ${/vide|non traduite|Langue/.test(x)?"b":"w"}">${esc(x)}</span>`).join("")}
<span class="tag">Confiance ${(r.confidence||0).toFixed(2)}</span></div>
<div class="pair"><div><div class="lbl">Source${r.locations&&r.locations[0]?" — "+esc(r.locations[0].src_label):""}</div>${esc(r.src)}</div><div><div class="lbl">Traduction${r.locations&&r.locations[0]?" — "+esc(r.locations[0].tgt_label):""}</div>${esc(r.tgt)}</div></div>
${r.alt?`<div class="extra"><b>Second traducteur :</b> ${esc(r.alt)}</div>`:""}${r.back?`<div class="extra"><b>Retraduction :</b> ${esc(r.back)}</div>`:""}</div>`).join("")
+(f.length>800?`<div class="empty">… ${f.length-800} autres : affinez la recherche.</div>`:""):`<div class="empty">Aucune phrase signalée.</div>`}
function toggleTheme(){const r=document.documentElement;const d=r.dataset.theme==="dark"||(!r.dataset.theme&&matchMedia("(prefers-color-scheme: dark)").matches);r.dataset.theme=d?"light":"dark"}
render();
</script></body></html>"""
