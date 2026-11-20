"""Every piece of source material, rendered so it can be judged by ear.

Two sections: the 43 original clips as they are, and all 70 atoms rendered into
the death slot (level-matched, no duration cap, 40 ms fade-out) so they can be
compared like for like.

  python build/all_options.py
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
VOICES = ROOT / "Voices"
ATOMS_DIR = ROOT / "atoms"
ATOMS_JSON = ROOT / "data" / "atoms.json"
SPEC = ROOT / "data" / "vanilla_spec.json"
OUT = ROOT / "data" / "all_options.html"
VANILLA_SFX = game.require(game.vanilla_sfx_dir(), "the extracted vanilla sfx tree",
                            game.EXTRACTOR_HINT)


def envelope(x, n=160):
    edges = np.linspace(0, len(x), n + 1).astype(int)
    e = np.array([np.sqrt((x[a:b] ** 2).mean()) if b > a else 0.0
                  for a, b in zip(edges[:-1], edges[1:])])
    m = e.max()
    return [int(round(v)) for v in (e / m * 100 if m > 0 else e)]


def data_uri(x, tmp, name):
    wav, ogg = Path(tmp) / f"{name}.wav", Path(tmp) / f"{name}.ogg"
    ffio.write_wav(wav, x)
    ffio.to_ogg(wav, ogg, bitrate="96k")
    return "data:audio/ogg;base64," + base64.b64encode(ogg.read_bytes()).decode()


def safe(s):
    return "".join(c if c.isalnum() else "_" for c in s)


def build():
    spec = {r["path"]: r for r in json.loads(SPEC.read_text(encoding="utf-8"))}
    atoms = json.loads(ATOMS_JSON.read_text(encoding="utf-8"))
    death = spec["player/isaac dies new.wav"]

    with tempfile.TemporaryDirectory() as tmp:
        van = ffio.read_wav(VANILLA_SFX / "player/isaac dies new.wav")
        ref = {"name": "香草死亡音", "detail": f"{death['dur']:.2f}s 参照",
               "dur": death["dur"], "env": envelope(van),
               "audio": data_uri(van, tmp, "van_death"), "ref": True}

        clips = []
        for mp3 in sorted(VOICES.glob("*.mp3")):
            x = dsp.trim_silence(ffio.decode(mp3))
            n = sum(1 for a in atoms if a["src"] == mp3.stem)
            clips.append({
                "name": mp3.stem,
                "detail": f"{len(x)/dsp.SR:.2f}s · 切出 {n} 个原子",
                "dur": len(x) / dsp.SR, "env": envelope(x),
                "audio": data_uri(x, tmp, "clip_" + safe(mp3.stem)), "ref": False,
            })

        rendered = []
        for a in sorted(atoms, key=lambda a: (a["src"], a["id"])):
            w = ffio.read_wav(ATOMS_DIR / f"{a['id']}.wav")
            y = dsp.fade(w, dsp.SR, 10.0, 40.0)
            y, _, short_db = dsp.match_rms(y, death["rms"])
            rendered.append({
                "name": a["id"],
                "detail": (f"{len(y)/dsp.SR:.2f}s · "
                           + (f"{a['f0']:.0f}Hz · " if a["f0"] else "无音高 · ")
                           + a["env_class"]
                           + (f" · 比原声轻 {-short_db:.1f}dB" if short_db < -3 else "")),
                "dur": len(y) / dsp.SR, "env": envelope(y),
                "audio": data_uri(y, tmp, "at_" + safe(a["id"])), "ref": False,
            })

    return [
        {"label": "43 段原始素材", "note": "trim 掉首尾静音后的完整片段，未做任何处理。"
                                          "括号里是它被切出了几个原子。",
         "items": clips},
        {"label": "70 个原子，全部渲染成死亡音", "note": "对齐到香草死亡音的响度、"
                                                    "10ms 淡入 40ms 淡出、不设时长上界。"
                                                    "第一行是香草原声作参照。",
         "items": [ref] + rendered},
    ]


PAGE_CSS = """
:root{--surface2:var(--stripe);--soft:var(--accent-soft)}
.h{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;padding-bottom:7px;border-bottom:2px solid var(--line)}
.h h2{font-family:var(--cond);font-weight:700;font-size:19px;margin:0;color:var(--accent)}
.h .note{font-size:13px;color:var(--ink2);flex-basis:100%}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:0 26px}
.row{display:grid;grid-template-columns:130px 1fr;gap:10px;align-items:center;
padding:8px 2px;border-bottom:1px solid var(--line)}
.row.ref{background:var(--surface2);padding-left:8px;padding-right:8px}
.n{font-family:var(--mono);font-size:12.5px;word-break:break-all}
.d{font-family:var(--mono);font-size:10.5px;color:var(--dim)}
@media(max-width:640px){.row{grid-template-columns:1fr;gap:4px}}
"""

PAGE = page_style.head("Miyamo Sound Bank", PAGE_CSS) + """<div class="wrap">
<header style="display:flex;flex-direction:column;gap:11px">
<div class="eyebrow">Miyamo voice SFX &middot; 全部素材</div>
<h1>手上有的全部声音</h1>
<p class="lede">上半部分是 43 段原始素材本身，下半部分是切出来的 70 个原子，
全部按死亡音的响度渲染、不设时长上界，所以彼此之间可以直接比较。</p>
<div class="how"><p><b>报 id 就行</b>，例如 <code>死亡 → long-2.00</code>。
想听某个原子装进别的槽位（受伤 / 坏药丸）也直接说。</p></div>
</header>
<div id="host"></div>
</div>
<script>
const DATA=/*__DATA__*/;
function envPath(e,w,h){const n=e.length;const p=e.map((v,i)=>[i/(n-1)*w,h-(v/100)*(h-2)-1]);
return "M0,"+h+"L"+p.map(q=>q[0].toFixed(1)+","+q[1].toFixed(1)).join("L")+"L"+w+","+h+"Z";}
document.getElementById("host").innerHTML=DATA.map(s=>
'<section><div class="h"><h2>'+s.label+'</h2><span class="note">'+s.note+'</span></div><div class="grid">'+
s.items.map(it=>'<div class="row'+(it.ref?' ref':'')+'">'+
'<div><div class="n">'+it.name+'</div><div class="d">'+it.detail+'</div></div>'+
'<div><audio controls preload="none" src="'+it.audio+'"></audio>'+
'<svg class="env" viewBox="0 0 300 18" preserveAspectRatio="none" aria-hidden="true">'+
'<path d="'+envPath(it.env,300,18)+'" fill="var(--soft)" stroke="var(--accent)" '+
'stroke-width="1" vector-effect="non-scaling-stroke"/></svg></div></div>').join("")+
'</div></section>').join("");
</script>
"""


if __name__ == "__main__":
    sections = build()
    OUT.write_text(PAGE.replace("/*__DATA__*/", json.dumps(sections, ensure_ascii=False)),
                   encoding="utf-8")
    print(f"{len(sections[0]['items'])} clips + {len(sections[1]['items']) - 1} atoms "
          f"-> {OUT} ({OUT.stat().st_size / 1e6:.2f} MB)")
