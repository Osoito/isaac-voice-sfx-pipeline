"""Candidates for the 8 fart / burp sounds.

`only=["cough"]` leaves three atoms for a five-member group, so the current
build tells variants apart by pitch. This page puts that against the wider pool
the category used before the restriction, so the choice can be made by ear.

  python build/fart_options.py
"""

import base64
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build import auto, dsp, ffio, game, page_style

ROOT = Path(__file__).resolve().parent.parent
ATOMS_DIR = ROOT / "atoms"
SPEC = ROOT / "data" / "vanilla_spec.json"
ATOMS = ROOT / "data" / "atoms.json"
AUTO = ROOT / "data" / "auto_map.json"
OUT = ROOT / "data" / "fart.html"
VANILLA_SFX = game.require(game.vanilla_sfx_dir(), "the extracted vanilla sfx tree",
                            game.EXTRACTOR_HINT)

# Sources worth hearing here: the current restriction, plus what the category
# drew on before it.
POOLS = [("cough", "cough（现在唯一允许的）"),
         ("belly", "belly 肚子叫"),
         ("gulp", "gulp 吞咽")]
PITCHES = [0.0, -4.0, -7.0]


def envelope(x, n=120):
    edges = np.linspace(0, len(x), n + 1).astype(int)
    e = np.array([np.sqrt((x[a:b] ** 2).mean()) if b > a else 0.0
                  for a, b in zip(edges[:-1], edges[1:])])
    m = e.max()
    return [int(round(v)) for v in (e / m * 100 if m > 0 else e)]


def uri(x, tmp, name):
    wav, ogg = Path(tmp) / f"{name}.wav", Path(tmp) / f"{name}.ogg"
    ffio.write_wav(wav, x)
    ffio.to_ogg(wav, ogg, bitrate="96k")
    return "data:audio/ogg;base64," + base64.b64encode(ogg.read_bytes()).decode()


def safe(s):
    return "".join(c if c.isalnum() else "_" for c in s)


def build():
    spec = [r for r in json.loads(SPEC.read_text(encoding="utf-8"))
            if auto.category(r["path"]) == "E1"]
    spec.sort(key=lambda r: r["path"])
    atoms = {a["id"]: a for a in json.loads(ATOMS.read_text(encoding="utf-8"))}
    cur = json.loads(AUTO.read_text(encoding="utf-8"))

    pool_atoms = [a for a in atoms.values()
                  if a["src"] in {p for p, _ in POOLS}]

    sections = []
    with tempfile.TemporaryDirectory() as tmp:
        for row in spec:
            van = ffio.read_wav(VANILLA_SFX / row["path"])
            items = [{
                "name": "香草原声", "detail": f"{row['dur']:.2f}s · {row['env_class']}",
                "cur": False, "van": True, "dur": row["dur"],
                "env": envelope(van), "audio": uri(van, tmp, "v" + safe(row["path"])),
            }]
            now = cur.get(row["path"], {})
            now_key = (now.get("atoms", [None])[0], now.get("semitones", 0.0))

            for a in sorted(pool_atoms, key=lambda a: (a["src"], a["id"])):
                for st in PITCHES:
                    w = ffio.read_wav(ATOMS_DIR / f"{a['id']}.wav")
                    y = dsp.pitch_shift(w, st) if st else w
                    y = dsp.fade(y, dsp.SR, 3.0, 12.0)
                    y, _, _ = dsp.match_rms(y, row["rms"])
                    is_cur = (a["id"], st) == now_key
                    items.append({
                        "name": a["id"] + (f"  {st:+.0f} st" if st else ""),
                        "detail": f"{len(y)/dsp.SR:.2f}s · {a['env_class']}",
                        "cur": is_cur, "van": False, "dur": len(y) / dsp.SR,
                        "env": envelope(y),
                        "audio": uri(y, tmp, f"c{safe(row['path'])}{safe(a['id'])}{int(st)}"),
                    })
            sections.append({"path": row["path"], "items": items})
    return sections


PAGE_CSS = """
:root{--surface2:var(--stripe);--soft:var(--accent-soft);--cur:#404040;--cursoft:rgba(64,64,64,.18)}
.h{font-family:var(--cond);font-weight:700;font-size:18px;color:var(--accent);
border-bottom:2px solid var(--line);padding-bottom:6px;margin-bottom:2px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:0 24px}
.row{display:grid;grid-template-columns:120px 1fr;gap:9px;align-items:center;
padding:7px 2px;border-bottom:1px solid var(--line)}
.row.van{background:var(--surface2);padding-left:8px;padding-right:8px}
.row.cur{background:var(--cursoft)}
.n{font-family:var(--mono);font-size:12px;word-break:break-all}
.row.cur .n::after{content:" ← 现在";color:var(--cur);font-weight:500}
.d{font-family:var(--mono);font-size:10px;color:var(--dim)}
@media(max-width:620px){.row{grid-template-columns:1fr;gap:3px}}
"""

PAGE = page_style.head("Fart Candidates", PAGE_CSS) + """<div class="wrap">
<header style="display:flex;flex-direction:column;gap:11px">
<div class="eyebrow">Miyamo voice SFX &middot; E1 放屁/打嗝</div>
<h1>8 个放屁音，挑一遍</h1>
<p class="lede">绿底那行是现在装在游戏里的。<code>cough</code> 只有 3 个原子而
<code>fart 1-5</code> 是同一编号组的 5 个变体，所以现在靠变调区分。
<code>belly</code> 和 <code>gulp</code> 是你限定「只要 cough」之前这一类会用到的，一并列出来对比。</p>
<div class="how"><p><b>按文件报</b>，例如 <code>fart 2 → belly.00 -4st</code>；
或者整类一句话，例如 <code>全部只用 cough.02 系列</code>、<code>gurg 那两个改用 belly</code>。</p></div>
</header>
<div id="host"></div>
</div>
<script>
const DATA=/*__DATA__*/;
function envPath(e,w,h){const n=e.length;const p=e.map((v,i)=>[i/(n-1)*w,h-(v/100)*(h-2)-1]);
return "M0,"+h+"L"+p.map(q=>q[0].toFixed(1)+","+q[1].toFixed(1)).join("L")+"L"+w+","+h+"Z";}
document.getElementById("host").innerHTML=DATA.map(s=>
'<section><div class="h">'+s.path+'</div><div class="grid">'+
s.items.map(it=>'<div class="row'+(it.van?' van':'')+(it.cur?' cur':'')+'">'+
'<div><div class="n">'+it.name+'</div><div class="d">'+it.detail+'</div></div>'+
'<div><audio controls preload="none" src="'+it.audio+'"></audio>'+
'<svg class="env" viewBox="0 0 300 16" preserveAspectRatio="none" aria-hidden="true">'+
'<path d="'+envPath(it.env,300,16)+'" fill="var(--soft)" stroke="var(--accent)" '+
'stroke-width="1" vector-effect="non-scaling-stroke"/></svg></div></div>').join("")+
'</div></section>').join("");
</script>
"""

if __name__ == "__main__":
    sections = build()
    OUT.write_text(PAGE.replace("/*__DATA__*/", json.dumps(sections, ensure_ascii=False)),
                   encoding="utf-8")
    n = sum(len(s["items"]) - 1 for s in sections)
    print(f"{len(sections)} targets x {n // len(sections)} candidates -> {OUT} "
          f"({OUT.stat().st_size / 1e6:.2f} MB)")
