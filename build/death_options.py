"""Render treatments for the death cry and build a picking page.

The source recording (wusodaro) ends abruptly with no tail left to take, so any
extension has to be synthesised. Isaac's death sound fires once per run and can
never overlap itself, so the duration bound that applies to hurt sounds does not
apply here at all.

  python build/death_options.py
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
ATOM = ROOT / "atoms" / "wusodaro.00.wav"
SPEC = ROOT / "data" / "vanilla_spec.json"
OUT = ROOT / "data" / "death.html"
VANILLA_SFX = game.require(game.vanilla_sfx_dir(), "the extracted vanilla sfx tree",
                            game.EXTRACTOR_HINT)

# (key, label, tail_ms, fade_in_ms, fade_out_ms, note)
TREATMENTS = [
    ("now", "现在装在游戏里的",
     0, 2, 8, "被 1.05x 上界截断，−2 半音那版切掉了词尾"),
    ("A", "A · 解除时长上界，短淡出",
     0, 10, 40, "完整一句，40ms 淡出。最保守。"),
    ("B", "B · 解除上界，长淡出",
     0, 10, 180, "180ms 淡出，从词内部就开始收，尾巴更软但词也更糊"),
    ("C", "C · 合成尾巴 250ms",
     250, 10, 30, "末尾 120ms 倒放并指数衰减，接在后面当作释放音"),
    ("D", "D · 合成尾巴 450ms",
     450, 10, 30, "同上但更长，接近混响尾"),
]

VARIANTS = [
    ("isaac dies new.wav", 0.0),
    ("isaac dies new 1.wav", -2.0),
    ("isaac dies new 2.wav", 2.0),
]


def envelope(x, n=200):
    edges = np.linspace(0, len(x), n + 1).astype(int)
    e = np.array([np.sqrt((x[a:b] ** 2).mean()) if b > a else 0.0
                  for a, b in zip(edges[:-1], edges[1:])])
    m = e.max()
    return [int(round(v)) for v in (e / m * 100 if m > 0 else e)]


def data_uri(x, tmp, name):
    wav, ogg = Path(tmp) / f"{name}.wav", Path(tmp) / f"{name}.ogg"
    ffio.write_wav(wav, x)
    ffio.to_ogg(wav, ogg)
    return "data:audio/ogg;base64," + base64.b64encode(ogg.read_bytes()).decode()


def render(atom, semis, tail_ms, fin, fout, cap_seconds):
    y = dsp.pitch_shift(atom, semis) if semis else np.array(atom)
    if tail_ms:
        y = dsp.extend_tail(y, dsp.SR, tail_ms)
    y = dsp.fade(y, dsp.SR, fin, fout)
    if cap_seconds is not None:
        y = dsp.fit_duration(y, dsp.SR, cap_seconds)
    return y


def build():
    spec = {r["path"]: r for r in json.loads(SPEC.read_text(encoding="utf-8"))}
    atom = ffio.read_wav(ATOM)
    sections = []
    with tempfile.TemporaryDirectory() as tmp:
        van_row = spec["player/isaac dies new.wav"]
        van = ffio.read_wav(VANILLA_SFX / "player/isaac dies new.wav")
        ref = {"key": "vanilla", "label": "香草原声", "note": "参照",
               "items": [{"name": "isaac dies new.wav",
                          "dur": van_row["dur"], "env": envelope(van),
                          "audio": data_uri(van, tmp, "van_death")}]}
        sections.append(ref)

        for key, label, tail, fin, fout, note in TREATMENTS:
            items = []
            for path, semis in VARIANTS:
                row = spec[f"player/{path}"]
                cap = row["dur"] * 1.05 if key == "now" else None
                y = render(atom, semis, tail, fin, fout, cap)
                y, _, _ = dsp.match_rms(y, row["rms"])
                items.append({
                    "name": f"{path}  ({semis:+.0f} st)",
                    "dur": len(y) / dsp.SR, "env": envelope(y),
                    "audio": data_uri(y, tmp, f"{key}_{path[:-4].replace(' ', '_')}"),
                })
            sections.append({"key": key, "label": label, "note": note,
                             "items": items})
    return sections


PAGE_CSS = """
:root{--surface2:var(--stripe);--soft:var(--accent-soft)}
section{display:flex;flex-direction:column}
.h{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;padding-bottom:7px;border-bottom:2px solid var(--line)}
.h h2{font-family:var(--cond);font-weight:700;font-size:19px;margin:0;color:var(--accent)}
.h .note{font-size:13px;color:var(--ink2);flex-basis:100%}
.row{display:grid;grid-template-columns:210px minmax(200px,1fr) 70px;gap:14px;align-items:center;
padding:9px 4px;border-bottom:1px solid var(--line)}
section.van .row{background:var(--surface2);padding-left:10px;padding-right:10px}
.n{font-family:var(--mono);font-size:12.5px}
.d{font-family:var(--mono);font-size:12px;color:var(--dim);text-align:right;font-variant-numeric:tabular-nums}
@media(max-width:720px){.row{grid-template-columns:1fr}.d{text-align:left}}
"""

PAGE = page_style.head("Death Cry Treatments", PAGE_CSS) + """<div class="wrap">
<header style="display:flex;flex-direction:column;gap:11px">
<div class="eyebrow">Miyamo voice SFX &middot; 死亡音处理</div>
<h1>「嘘だろ」该怎么收尾</h1>
<p class="lede">源录音本身就是硬切的，末尾没有余量可取，所以任何"延长"都只能是合成的。
死亡音一局只响一次、不可能自我叠加，所以除了「现在」那一组，其余都<b>不受时长上界约束</b>，
三个变体都是完整一句。</p>
</header>
<div id="host"></div>
</div>
<script>
const DATA=/*__DATA__*/;
function envPath(e,w,h){const n=e.length;const p=e.map((v,i)=>[i/(n-1)*w,h-(v/100)*(h-2)-1]);
return "M0,"+h+"L"+p.map(q=>q[0].toFixed(1)+","+q[1].toFixed(1)).join("L")+"L"+w+","+h+"Z";}
document.getElementById("host").innerHTML=DATA.map(s=>
'<section class="'+(s.key==="vanilla"?"van":"")+'"><div class="h"><h2>'+s.label+'</h2>'+
'<span class="note">'+s.note+'</span></div>'+
s.items.map(it=>'<div class="row"><div class="n">'+it.name+'</div>'+
'<div><audio controls preload="none" src="'+it.audio+'"></audio>'+
'<svg class="env" viewBox="0 0 400 24" preserveAspectRatio="none" aria-hidden="true">'+
'<path d="'+envPath(it.env,400,24)+'" fill="var(--soft)" stroke="var(--accent)" '+
'stroke-width="1" vector-effect="non-scaling-stroke"/></svg></div>'+
'<div class="d">'+it.dur.toFixed(2)+'s</div></div>').join("")+'</section>').join("");
</script>
"""


if __name__ == "__main__":
    sections = build()
    OUT.write_text(PAGE.replace("/*__DATA__*/", json.dumps(sections, ensure_ascii=False)),
                   encoding="utf-8")
    print(f"{len(sections) - 1} treatments x 3 variants -> {OUT} "
          f"({OUT.stat().st_size / 1e6:.2f} MB)")
    for s in sections[1:]:
        print(f"  {s['key']:<5} " + "  ".join(f"{i['dur']:.2f}s" for i in s["items"]))
