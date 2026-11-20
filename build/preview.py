"""Preview one category: vanilla against replacement, one row per file.

  python build/preview.py F
  python build/preview.py D7

Every row pairs the game's own sound with what this build put in its place, so a
wrong match is obvious by ear rather than by reading atom ids.
"""

import base64
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build import auto, ffio, game, page_style

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "data" / "build_report.json"
MOD_SFX = ROOT / "mod" / "resources" / "sfx"
VANILLA_SFX = game.require(game.vanilla_sfx_dir(), "the extracted vanilla sfx tree",
                            game.EXTRACTOR_HINT)


def envelope(x, n=140):
    edges = np.linspace(0, len(x), n + 1).astype(int)
    e = np.array([np.sqrt((x[a:b] ** 2).mean()) if b > a else 0.0
                  for a, b in zip(edges[:-1], edges[1:])])
    m = e.max()
    return [int(round(v)) for v in (e / m * 100 if m > 0 else e)]


def uri(path, tmp, name):
    ogg = Path(tmp) / f"{name}.ogg"
    ffio.to_ogg(path, ogg, bitrate="96k")
    return "data:audio/ogg;base64," + base64.b64encode(ogg.read_bytes()).decode()


def safe(s):
    return "".join(c if c.isalnum() else "_" for c in s)


def build(cats):
    want = set(cats)
    rows = [r for r in json.loads(REPORT.read_text(encoding="utf-8"))
            if r["cat"] in want]
    rows.sort(key=lambda r: r["path"])
    items = []
    with tempfile.TemporaryDirectory() as tmp:
        for r in rows:
            vp, mp = VANILLA_SFX / r["path"], MOD_SFX / r["path"]
            items.append({
                "path": r["path"], "cat": r["cat"],
                "atoms": r["atoms"],
                "van_dur": r["van_dur"], "dur": r["dur"],
                "van_env": envelope(ffio.read_wav(vp)),
                "env": envelope(ffio.read_wav(mp)),
                "van_audio": uri(vp, tmp, "v" + safe(r["path"])),
                "audio": uri(mp, tmp, "m" + safe(r["path"])),
            })
    return items


PAGE_CSS = """
.hdr{display:grid;grid-template-columns:1fr 1fr;gap:16px;font-family:var(--mono);font-size:11px;
letter-spacing:.06em;color:#fff;background:#000;padding:3px 8px;position:sticky;top:0}
.item{border:1px solid var(--line);border-top:none;padding:9px 8px}
.item:nth-child(odd){background:var(--stripe)}
.top{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:7px}
.p{font-family:var(--mono);font-size:13px;font-weight:700}
.a{font-family:var(--mono);font-size:11px;color:var(--accent)}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.cell .lab{font-family:var(--mono);font-size:10.5px;color:var(--dim);margin-bottom:3px}
/* The two sides of every row: the game's own file against the replacement. */
.cell:first-child .env path{stroke:#404040;fill:rgba(64,64,64,.18)}
.cell:nth-child(2) .env path{stroke:var(--accent);fill:var(--accent-soft)}
@media(max-width:720px){.pair,.hdr{grid-template-columns:1fr}.hdr span:last-child{display:none}}
"""

PAGE = page_style.head("__TITLE__", PAGE_CSS) + """<div class="wrap">
<header style="display:flex;flex-direction:column;gap:11px">
<div class="eyebrow">Miyamo voice SFX &middot; __CAT__ 逐个检查</div>
<h1>__HEAD__</h1>
<p class="lede">左边是游戏原声，右边是这一版装进去的替换品。小字是用到的原子 id。</p>
</header>
<div class="hdr"><span>香草原声</span><span>替换品</span></div>
<div id="host"></div>
</div>
<script>
const DATA=/*__DATA__*/;
function envPath(e,w,h){const n=e.length;const p=e.map((v,i)=>[i/(n-1)*w,h-(v/100)*(h-2)-1]);
return "M0,"+h+"L"+p.map(q=>q[0].toFixed(1)+","+q[1].toFixed(1)).join("L")+"L"+w+","+h+"Z";}
document.getElementById("host").innerHTML=DATA.map((it,i)=>
'<div class="item"><div class="top"><span class="p">'+(i+1)+'. '+it.path+'</span>'+
'<span class="a">'+it.atoms.join(" + ")+'</span></div><div class="pair">'+
'<div class="cell"><div class="lab">原声 '+it.van_dur.toFixed(2)+'s</div>'+
'<audio controls preload="none" src="'+it.van_audio+'"></audio>'+
'<svg class="env" viewBox="0 0 400 22" preserveAspectRatio="none" aria-hidden="true">'+
'<path d="'+envPath(it.van_env,400,22)+'" fill="var(--vsoft)" stroke="var(--van)" '+
'stroke-width="1" vector-effect="non-scaling-stroke"/></svg></div>'+
'<div class="cell"><div class="lab">替换 '+it.dur.toFixed(2)+'s</div>'+
'<audio controls preload="none" src="'+it.audio+'"></audio>'+
'<svg class="env" viewBox="0 0 400 22" preserveAspectRatio="none" aria-hidden="true">'+
'<path d="'+envPath(it.env,400,22)+'" fill="var(--nsoft)" stroke="var(--new)" '+
'stroke-width="1" vector-effect="non-scaling-stroke"/></svg></div>'+
'</div></div>').join("");
</script>
"""

# Browser title, then the heading. The heading takes the row count from the data,
# because a number written here goes stale the moment the mapping changes.
TITLES = {"F": ("Misc Creature Check", "{n} 个杂项生物音")}

if __name__ == "__main__":
    cats = (sys.argv[1] if len(sys.argv) > 1 else "F").split(",")
    cat = "_".join(cats)
    items = build(cats)
    title, head = TITLES.get(cat, (f"{cat} Check",
        " · ".join(f"{c} {auto.HINTS[c]['label']}" for c in cats)))
    head = head.format(n=len(items)) if "{n}" in head else head
    out = ROOT / "data" / f"preview_{cat}.html"
    out.write_text(
        PAGE.replace("__TITLE__", title).replace("__CAT__", cat)
            .replace("__HEAD__", head)
            .replace("/*__DATA__*/", json.dumps(items, ensure_ascii=False)),
        encoding="utf-8")
    print(f"{len(items)} pairs -> {out} ({out.stat().st_size / 1e6:.2f} MB)")
