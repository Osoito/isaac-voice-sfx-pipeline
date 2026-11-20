"""The look of the audition pages. The only place the palette and the chrome live.

Every page script builds its head from `head()`. Before this module the palette and
the font stack were a literal in six scripts, so changing a colour meant six edits
and the sixth was the one that got missed.

The look is a late-90s utility page: a bordered white panel on a tiled ground, a
black header bar, striped rows with real borders, and a kai display face for
the heading. It has no dark mode, on purpose. A paper panel is the whole idea.

A page adds its own layout rules and its own accent tokens on top. The names differ
by page because what is being compared differs: preview has vanilla against
replacement, the option pages have a current pick against candidates.
"""

# 华文楷体 (family name "STKaiti"). These pages are simplified Chinese, so the
# heavier 超世纪粗标楷 ("JetLink BoldStdKai") is the wrong tool: it is cut for
# traditional Chinese and Japanese.
DISPLAY_STACK = '"STKaiti","华文楷体","KaiTi","SimKai",serif'

TOKENS = """
:root{
--ground:#b8b4a8;--panel:#ffffff;--stripe:#f4f2ea;--line:#6e6a60;
--ink:#101010;--ink2:#303030;--dim:#55524c;
--accent:#000080;--accent-soft:rgba(0,0,128,.15);
--sans:"SimSun","宋体",serif;
--cond:%s;
--mono:"Courier New",monospace;}
""" % DISPLAY_STACK

# An 8px tile with two off-colour pixels. Cheap, and it stops the ground reading
# as a flat fill, which is most of what makes a page look generated.
GROUND_TILE = (
    "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' "
    "width='8' height='8'><rect width='8' height='8' fill='%23b8b4a8'/>"
    "<rect width='1' height='1' fill='%23a8a498'/>"
    "<rect x='4' y='4' width='1' height='1' fill='%23c4c0b4'/></svg>\")"
)

CHROME = """
*{box-sizing:border-box}
body{background:var(--ground) %s repeat;color:var(--ink);
font-family:var(--sans);font-size:13px;line-height:1.45}
.wrap{max-width:900px;margin:20px auto;background:var(--panel);border:2px solid #000;
box-shadow:4px 4px 0 rgba(0,0,0,.35);padding:20px 20px 34px;
display:flex;flex-direction:column;gap:16px}
h1{font-family:var(--cond);font-weight:400;font-size:34px;margin:0;letter-spacing:.02em;
border-bottom:3px double #000;padding-bottom:6px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.08em;color:#333;
background:#e4e0d4;border:1px solid var(--line);display:inline-block;padding:1px 7px}
.lede{max-width:62ch;color:var(--ink2);margin:0}
.how{border:2px ridge #9a9589;border-left:4px solid var(--accent);background:#f2efe4;
padding:9px 12px;max-width:64ch}
.how p{margin:0}
audio{width:100%%;height:30px;filter:grayscale(1) contrast(1.1)}
.env{display:block;width:100%%;height:22px;margin-top:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
""" % GROUND_TILE

_HEAD = """<title>%(title)s</title>
<style>%(tokens)s%(chrome)s%(page)s</style>
"""


def head(title, page_css=""):
    """The whole <head> for a page: title, tokens, shared chrome, page rules.

    No webfont link. Every face this uses is already on the machine, so the page
    stays a single file that works with no network.
    """
    return _HEAD % {"title": title, "tokens": TOKENS,
                    "chrome": CHROME, "page": page_css}
