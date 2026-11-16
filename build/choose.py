"""Render candidate replacements for the player sounds and build a picking page.

The point of this script is to put real audio in front of a human fast. For each
player sound group it renders every plausible atom into that slot, matched to the
vanilla file's duration bound and level, so the choice is made by listening
rather than by reading filenames.

  python build/choose.py
"""

import base64
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build import dsp, ffio

ROOT = Path(__file__).resolve().parent.parent
ATOMS_DIR = ROOT / "atoms"
ATOMS_JSON = ROOT / "data" / "atoms.json"
SPEC_JSON = ROOT / "data" / "vanilla_spec.json"
OUT_HTML = ROOT / "data" / "choose.html"
VANILLA_SFX = Path(
    "D:/softwares/Steam/steamapps/common/The Binding of Isaac Rebirth"
    "/extracted_resources/resources/sfx")

# The four player groups, with a plain-language note on when the player hears it.
GROUPS = [
    ("player/hurt grunt", "受伤", "全游戏最高频的音效，每分钟响很多次"),
    ("player/baby hurt", "受伤(婴儿角色)", "同上，但用于婴儿类角色"),
    ("player/derp", "吃到坏药丸", "偶发，可以更有戏"),
    ("player/isaac dies new", "死亡", "一局一次，可以用完整一句话"),
]

N_CANDIDATES = 12


def envelope(x, n=140):
    edges = np.linspace(0, len(x), n + 1).astype(int)
    e = np.array([np.sqrt((x[a:b] ** 2).mean()) if b > a else 0.0
                  for a, b in zip(edges[:-1], edges[1:])])
    m = e.max()
    return [int(round(v)) for v in (e / m * 100 if m > 0 else e)]


def data_uri(x, tmp, name):
    wav = Path(tmp) / f"{name}.wav"
    ogg = Path(tmp) / f"{name}.ogg"
    ffio.write_wav(wav, x)
    ffio.to_ogg(wav, ogg)
    return "data:audio/ogg;base64," + base64.b64encode(ogg.read_bytes()).decode()


def pick_candidates(atoms, target_dur, n=N_CANDIDATES):
    """Closest duration first, one atom per source clip so the list is varied."""
    seen, out = set(), []
    for a in sorted(atoms, key=lambda a: abs(a["dur"] - target_dur)):
        if a["src"] in seen:
            continue
        seen.add(a["src"])
        out.append(a)
        if len(out) >= n:
            break
    return out


def render(atom_wave, target_rms, max_seconds):
    y = dsp.fade(atom_wave, dsp.SR, 2.0, 8.0)
    y = dsp.fit_duration(y, dsp.SR, max_seconds)
    y, _, short_db = dsp.match_rms(y, target_rms)
    return y, short_db


def build():
    atoms = json.loads(ATOMS_JSON.read_text(encoding="utf-8"))
    spec = json.loads(SPEC_JSON.read_text(encoding="utf-8"))
    by_group = {}
    for r in spec:
        by_group.setdefault(r["group"], []).append(r)

    sections = []
    with tempfile.TemporaryDirectory() as tmp:
        for gname, label, note in GROUPS:
            rows = sorted(by_group[gname], key=lambda r: r["path"])
            ref = rows[0]
            van = ffio.read_wav(VANILLA_SFX / ref["path"])
            items = [{
                "id": "vanilla",
                "src": "香草原声",
                "detail": f"{ref['dur']:.2f}s · rms {ref['rms']:.3f}",
                "dur": ref["dur"], "short_db": 0.0, "vanilla": True,
                "env": envelope(van),
                "audio": data_uri(van, tmp, f"van_{gname.replace('/', '_')}"),
            }]
            for a in pick_candidates(atoms, ref["dur"]):
                w = ffio.read_wav(ATOMS_DIR / f"{a['id']}.wav")
                y, short_db = render(w, ref["rms"],
                                     ref["dur"] * 1.05)
                items.append({
                    "id": a["id"],
                    "src": a["src"],
                    "detail": (f"{len(y)/dsp.SR:.2f}s · "
                               + (f"{a['f0']:.0f}Hz · " if a["f0"] else "无音高 · ")
                               + f"原子 {a['dur']:.2f}s"),
                    "dur": len(y) / dsp.SR, "short_db": short_db, "vanilla": False,
                    "env": envelope(y),
                    "audio": data_uri(y, tmp, f"c_{a['id']}_{gname.replace('/', '_')}"),
                })
            sections.append({
                "group": gname, "label": label, "note": note,
                "files": [r["path"] for r in rows], "items": items,
            })
    return sections


PAGE = """<title>Isaac Voice Picks</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500&display=swap">
<style>
:root{--ground:#F1F0EC;--surface:#FBFAF8;--surface2:#E7E5DE;--line:#D8D5CC;
--ink:#1B1A17;--ink2:#4A4842;--dim:#7C7970;--accent:#B5400C;--accent-soft:rgba(181,64,12,.13);--good:#2F6B3A;
--sans:"IBM Plex Sans",system-ui,sans-serif;--cond:"IBM Plex Sans Condensed",var(--sans);
--mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--ground:#131316;--surface:#1A1A1E;
--surface2:#232329;--line:#2E2E35;--ink:#EBE9E4;--ink2:#B6B3AC;--dim:#8B8880;--accent:#FF8154;
--accent-soft:rgba(255,129,84,.16);--good:#6FCB85;}}
:root[data-theme=dark]{--ground:#131316;--surface:#1A1A1E;--surface2:#232329;--line:#2E2E35;
--ink:#EBE9E4;--ink2:#B6B3AC;--dim:#8B8880;--accent:#FF8154;--accent-soft:rgba(255,129,84,.16);--good:#6FCB85;}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.55}
.wrap{max-width:1000px;margin:0 auto;padding:36px 22px 64px;display:flex;flex-direction:column;gap:34px}
h1{font-family:var(--cond);font-weight:700;font-size:clamp(27px,4vw,38px);margin:0;letter-spacing:-.015em}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:var(--dim)}
.lede{max-width:60ch;color:var(--ink2);margin:0}
.how{border-left:3px solid var(--accent);background:var(--accent-soft);padding:12px 16px;max-width:64ch}
.how p{margin:0}
section{display:flex;flex-direction:column}
.sec-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;padding-bottom:8px;
border-bottom:2px solid var(--line)}
.sec-head h2{font-family:var(--cond);font-weight:700;font-size:22px;margin:0;color:var(--accent)}
.sec-head .g{font-family:var(--mono);font-size:12px;color:var(--dim)}
.sec-head .note{font-size:13px;color:var(--ink2);flex-basis:100%}
.row{display:grid;grid-template-columns:150px minmax(200px,1fr) 190px;gap:16px;align-items:center;
padding:11px 4px;border-bottom:1px solid var(--line)}
.row.van{background:var(--surface2);padding-left:10px;padding-right:10px}
.name{font-family:var(--mono);font-size:14px;font-weight:500;color:var(--accent);word-break:break-all}
.row.van .name{color:var(--ink)}
.detail{font-family:var(--mono);font-size:11px;color:var(--dim)}
audio{width:100%;height:32px}
.env{display:block;width:100%;height:26px;margin-top:5px}
.warn{font-family:var(--mono);font-size:11px;color:var(--dim)}
a{color:inherit}:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media(max-width:760px){.row{grid-template-columns:1fr;gap:8px}}
</style>
<div class="wrap">
<header style="display:flex;flex-direction:column;gap:12px">
<div class="eyebrow">Miyamo voice SFX mod &middot; 选音频</div>
<h1>Isaac 该用哪一声？</h1>
<p class="lede">四组主角音效，每组第一行是香草原声作参照，下面是从 70 个语音原子里按时长匹配挑出的候选。
每个候选都已经按该音效的时长上限截断、并对齐到原声响度，所以你听到的就是装进游戏后的样子。</p>
<div class="how"><p><b>怎么回我：</b>每组报一个原子 id 就行，比如
<code>受伤 → iya.00，死亡 → yayamero.01</code>。一组想要多个（同组的编号变体游戏会随机播）就都报上。</p></div>
</header>
<div id="host"></div>
</div>
<script>
const DATA=/*__DATA__*/;
function envPath(e,w,h){const n=e.length;const p=e.map((v,i)=>[i/(n-1)*w,h-(v/100)*(h-2)-1]);
return "M0,"+h+"L"+p.map(q=>q[0].toFixed(1)+","+q[1].toFixed(1)).join("L")+"L"+w+","+h+"Z";}
document.getElementById("host").innerHTML=DATA.map(s=>
'<section><div class="sec-head"><h2>'+s.label+'</h2>'+
'<span class="g">'+s.group+' &middot; '+s.files.length+' 个文件</span>'+
'<span class="note">'+s.note+'</span></div>'+
s.items.map(it=>'<div class="row'+(it.vanilla?' van':'')+'">'+
'<div><div class="name">'+it.id+'</div><div class="detail">'+it.detail+'</div></div>'+
'<div><audio controls preload="none" src="'+it.audio+'"></audio>'+
'<svg class="env" viewBox="0 0 400 26" preserveAspectRatio="none" aria-hidden="true">'+
'<path d="'+envPath(it.env,400,26)+'" fill="var(--accent-soft)" stroke="var(--accent)" '+
'stroke-width="1" vector-effect="non-scaling-stroke"/></svg></div>'+
'<div class="warn">'+(it.vanilla?'参照':(it.short_db<-3?('比原声轻 '+(-it.short_db).toFixed(1)+' dB'):'响度已对齐'))+'</div>'+
'</div>').join("")+'</section>').join("");
</script>
"""


if __name__ == "__main__":
    sections = build()
    OUT_HTML.write_text(
        PAGE.replace("/*__DATA__*/", json.dumps(sections, ensure_ascii=False)),
        encoding="utf-8")
    n = sum(len(s["items"]) - 1 for s in sections)
    print(f"{n} candidates across {len(sections)} groups -> {OUT_HTML} "
          f"({OUT_HTML.stat().st_size / 1e6:.2f} MB)")
