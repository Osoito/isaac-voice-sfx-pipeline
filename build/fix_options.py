"""Candidates for two open F-category questions.

16 `dog howell` wants to read as a howl: a long, pitched, continuous glide. The
source clips are speech, so the ingredients are the most sustained voiced atoms,
pitched down (resampling lengthens them at the same time) and joined with
crossfades long enough that the seam stops sounding like a new word.

17/18 `fat grunt 1` and `fat grunt 2` are one numbered group, so the engine picks
between them at random. They should come from the same clip to sound like one
creature, while staying different enough that the randomisation still does
something.

  python build/fix_options.py
"""

import base64
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build import dsp, ffio, game, page_style

ROOT = Path(__file__).resolve().parent.parent
ATOMS_DIR = ROOT / "atoms"
SPEC = ROOT / "data" / "vanilla_spec.json"
OUT = ROOT / "data" / "fix.html"
VANILLA_SFX = game.require(game.vanilla_sfx_dir(), "the extracted vanilla sfx tree",
                            game.EXTRACTOR_HINT)

# (key, [(atom, semitones), ...], xfade_ms, note)
HOWL = [
    ("H1", [("long-5.00", -5)], 0, "单个最长原子降 5 度"),
    ("H2", [("long-5.00", -10)], 0, "同上降 10 度，更长更低"),
    ("H3", [("long-5.00", -5), ("long-5.00", -9)], 300,
     "同一原子两段、音高下滑，300ms 交叉淡化成一条连续音"),
    ("H4", [("onceuponatimeinamerica.02", -7), ("long-5.00", -7)], 300,
     "两个持续元音接成一条"),
    ("H5", [("long-5.00", -7), ("onceuponatimeinamerica.02", -10)], 350,
     "先高后低，模仿嚎叫的下坠"),
    ("H6", [("short-18.00", -12), ("long-5.00", -7), ("long-2.01", -9)], 300,
     "三段长滑音"),
    ("H7", [("onceuponatimeinamerica.02", -12)], 0, "低沉单音"),
    ("H8", [("long-5.00", -3), ("long-5.00", -7), ("long-5.00", -12)], 400,
     "三段连续下滑，最像狼嚎的形状"),
]

# (key, source label, [(atom for fat grunt 1, st), (atom for fat grunt 2, st)])
GRUNT = [
    ("G1", "long-2", [("long-2.01", 0), ("long-2.00", 0)]),
    ("G2", "long-2 降调", [("long-2.01", -4), ("long-2.00", -4)]),
    ("G3", "long-4", [("long-4.01", -3), ("long-4.00", -3)]),
    ("G4", "cough", [("cough.00", -3), ("cough.02", -3)]),
    ("G5", "onceuponatimeinamerica", [("onceuponatimeinamerica.00", -3),
                                      ("onceuponatimeinamerica.01", -3)]),
    ("G6", "sukisuki", [("sukisuki.01", -4), ("sukisuki.04", -4)]),
    ("G7", "short-13", [("short-13.00", -5), ("short-13.01", -5)]),
]


def envelope(x, n=140):
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


def render(recipe, xfade, target_rms):
    parts = []
    for atom_id, st in recipe:
        w = ffio.read_wav(ATOMS_DIR / f"{atom_id}.wav")
        parts.append(dsp.pitch_shift(w, st) if st else w)
    y = parts[0] if len(parts) == 1 else dsp.chain(parts, dsp.SR, xfade)
    y = dsp.fade(y, dsp.SR, 20.0, 60.0)
    y, _, _ = dsp.match_rms(y, target_rms)
    return y


def build():
    spec = {r["path"]: r for r in json.loads(SPEC.read_text(encoding="utf-8"))}
    sections = []
    with tempfile.TemporaryDirectory() as tmp:
        # --- 16 dog howell -------------------------------------------------
        row = spec["dog howell.wav"]
        van = ffio.read_wav(VANILLA_SFX / "dog howell.wav")
        items = [{"key": "vanilla", "name": "香草原声", "note": "参照",
                  "dur": row["dur"], "env": envelope(van),
                  "audio": uri(van, tmp, "v_howl"), "van": True, "cur": False}]
        cur = [("gulp.00", 0), ("long-3.00", 0), ("long-2.01", 0),
               ("wusodaro.00", 0)]
        y = render(cur, 18.0, row["rms"])
        items.append({"key": "now", "name": "现在装着的", "note": "自动匹配的结果",
                      "dur": len(y) / dsp.SR, "env": envelope(y),
                      "audio": uri(y, tmp, "n_howl"), "van": False, "cur": True})
        for key, recipe, xf, note in HOWL:
            y = render(recipe, xf or 18.0, row["rms"])
            items.append({
                "key": key,
                "name": " → ".join(f"{a}{st:+d}" for a, st in recipe),
                "note": note, "dur": len(y) / dsp.SR, "env": envelope(y),
                "audio": uri(y, tmp, "h_" + key), "van": False, "cur": False})
        sections.append({"title": "16 · dog howell",
                         "sub": f"原声 {row['dur']:.2f}s。要更像嚎叫：长、有音高、连续下滑。",
                         "items": items, "pair": False})

        # --- 17 / 18 fat grunt ---------------------------------------------
        r1, r2 = spec["fat grunt 1.wav"], spec["fat grunt 2.wav"]
        v1 = ffio.read_wav(VANILLA_SFX / "fat grunt 1.wav")
        v2 = ffio.read_wav(VANILLA_SFX / "fat grunt 2.wav")
        items = [{"key": "vanilla", "name": "香草原声", "note": "参照",
                  "van": True, "cur": False,
                  "a": {"dur": r1["dur"], "env": envelope(v1),
                        "audio": uri(v1, tmp, "v_fg1")},
                  "b": {"dur": r2["dur"], "env": envelope(v2),
                        "audio": uri(v2, tmp, "v_fg2")}}]
        n1 = render([("miyamo.00", 0), ("miyamoto.00", 0)], 18.0, r1["rms"])
        n2 = render([("short-18.00", 0)], 18.0, r2["rms"])
        items.append({"key": "now", "name": "现在装着的",
                      "note": "两个不同源，听起来不像同一只怪",
                      "van": False, "cur": True,
                      "a": {"dur": len(n1) / dsp.SR, "env": envelope(n1),
                            "audio": uri(n1, tmp, "n_fg1")},
                      "b": {"dur": len(n2) / dsp.SR, "env": envelope(n2),
                            "audio": uri(n2, tmp, "n_fg2")}})
        for key, label, (p1, p2) in GRUNT:
            ya = render([p1], 18.0, r1["rms"])
            yb = render([p2], 18.0, r2["rms"])
            items.append({
                "key": key, "name": label,
                "note": f"{p1[0]} {p1[1]:+d}st  /  {p2[0]} {p2[1]:+d}st",
                "van": False, "cur": False,
                "a": {"dur": len(ya) / dsp.SR, "env": envelope(ya),
                      "audio": uri(ya, tmp, "g1_" + key)},
                "b": {"dur": len(yb) / dsp.SR, "env": envelope(yb),
                      "audio": uri(yb, tmp, "g2_" + key)}})
        sections.append({
            "title": "17 / 18 · fat grunt 1 与 2",
            "sub": f"原声 {r1['dur']:.2f}s 与 {r2['dur']:.2f}s。同一编号组，"
                   f"游戏会在两者间随机播，所以要同源但不同声。",
            "items": items, "pair": True})
    return sections


PAGE_CSS = """
:root{--surface2:var(--stripe);--soft:var(--accent-soft);--cur:#404040;--cursoft:rgba(64,64,64,.18)}
.h{border-bottom:2px solid var(--line);padding-bottom:7px;margin-bottom:4px}
.h h2{font-family:var(--cond);font-weight:700;font-size:20px;margin:0;color:var(--accent)}
.h .sub{font-size:13px;color:var(--ink2);margin-top:3px}
.row{display:grid;grid-template-columns:80px 1fr;gap:14px;align-items:start;
padding:11px 4px;border-bottom:1px solid var(--line)}
.row.van{background:var(--surface2);padding-left:8px;padding-right:8px}
.row.cur{background:var(--cursoft)}
.k{font-family:var(--mono);font-size:14px;font-weight:500;color:var(--accent)}
.row.van .k,.row.cur .k{color:var(--ink)}
.nm{font-family:var(--mono);font-size:11.5px;word-break:break-all}
.nt{font-size:12px;color:var(--dim);margin-top:2px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:6px}
.lab{font-family:var(--mono);font-size:10px;color:var(--dim)}
@media(max-width:700px){.two{grid-template-columns:1fr}.row{grid-template-columns:1fr}}
"""

PAGE = page_style.head("Howl and Grunt Fixes", PAGE_CSS) + """<div class="wrap">
<header style="display:flex;flex-direction:column;gap:11px">
<div class="eyebrow">Miyamo voice SFX &middot; F 类返工</div>
<h1>嚎叫与胖怪哼声</h1>
<p class="lede">绿底是现在装在游戏里的，灰底是香草原声。
嚎叫那组全部降了调——重采样降调会同时拉长，正好把语音变成拖长的滑音；
交叉淡化拉到 300ms 以上，接缝就不再像是换了个词。</p>
<div class="how"><p><b>报编号</b>，例如 <code>16 用 H5，17/18 用 G3</code>。
也可以说「H8 但再低一点」，我调参数重烘。</p></div>
</header>
<div id="host"></div>
</div>
<script>
const DATA=/*__DATA__*/;
function envPath(e,w,h){const n=e.length;const p=e.map((v,i)=>[i/(n-1)*w,h-(v/100)*(h-2)-1]);
return "M0,"+h+"L"+p.map(q=>q[0].toFixed(1)+","+q[1].toFixed(1)).join("L")+"L"+w+","+h+"Z";}
function player(o,label){return '<div><div class="lab">'+label+' '+o.dur.toFixed(2)+'s</div>'+
'<audio controls preload="none" src="'+o.audio+'"></audio>'+
'<svg class="env" viewBox="0 0 400 22" preserveAspectRatio="none" aria-hidden="true">'+
'<path d="'+envPath(o.env,400,22)+'" fill="var(--soft)" stroke="var(--accent)" '+
'stroke-width="1" vector-effect="non-scaling-stroke"/></svg></div>';}
document.getElementById("host").innerHTML=DATA.map(s=>
'<section><div class="h"><h2>'+s.title+'</h2><div class="sub">'+s.sub+'</div></div>'+
s.items.map(it=>'<div class="row'+(it.van?' van':'')+(it.cur?' cur':'')+'">'+
'<div class="k">'+it.key+'</div><div><div class="nm">'+it.name+'</div>'+
'<div class="nt">'+it.note+'</div>'+
(s.pair?('<div class="two">'+player(it.a,"fat grunt 1")+player(it.b,"fat grunt 2")+'</div>')
       :player(it,""))+
'</div></div>').join("")+'</section>').join("");
</script>
"""

if __name__ == "__main__":
    sections = build()
    OUT.write_text(PAGE.replace("/*__DATA__*/", json.dumps(sections, ensure_ascii=False)),
                   encoding="utf-8")
    print(f"{len(HOWL)} howl + {len(GRUNT)} grunt options -> {OUT} "
          f"({OUT.stat().st_size / 1e6:.2f} MB)")
