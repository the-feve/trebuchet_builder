"""The "Order Trebuchet Supplies" page (/supplies): Amazon affiliate links.

Same layout as Rocket Builder's /ordersupplies (rocket-builder-web
server/supplies.py). The list is treb_gear.json: categories of items, each
with either an ASIN (one product) or a search (an Amazon search link), a
name, a note, an optional "pick" ("Start here") and the shopping-list keys it
covers. Every link carries the Associates Store ID. No prices or Amazon
images (only allowed through Amazon's API); each item shows a drawing of its
kind instead.

Named treb_* because the Rocket Builder app loads this server alongside its
own supplies module.
"""

from __future__ import annotations

import json
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import quote_plus

GEAR = Path(__file__).resolve().parent / "treb_gear.json"
DISCLOSURE = "As an Amazon Associate, I earn from qualifying purchases."
ROCKET_URL = "https://rocket.quiverdesignworks.net/"
TREBUCHET_URL = "https://trebuchet.quiverdesignworks.net/"


def amazon_url(item: dict, store_id: str) -> str:
    tag = f"tag={store_id}" if store_id else ""
    if item.get("asin"):
        return f"https://www.amazon.com/dp/{item['asin']}/" + (f"?{tag}" if tag else "")
    return f"https://www.amazon.com/s?k={quote_plus(item['search'])}" + (f"&{tag}" if tag else "")


_S = 'fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"'
ICONS = {
    "hardware": f'<path {_S} d="M20 10h24l6 10-6 10H20l-6-10zM28 30v26M36 30v26M28 38h8M28 46h8"/>',
    "sling": f'<path {_S} d="M8 10c6 20 10 30 22 36M56 10c-6 20-10 30-22 36"/><path {_S} d="M22 44q10 10 20 0"/><circle {_S} cx="32" cy="46" r="6"/>',
    "weight": f'<path {_S} d="M18 26h28l6 30H12zM26 26a6 6 0 0 1 12 0"/><path {_S} d="M24 42h16"/>',
    "projectiles": f'<circle {_S} cx="22" cy="40" r="12"/><circle {_S} cx="46" cy="22" r="8"/><path {_S} d="M30 10q8-2 10 4"/>',
    "filament": f'<circle {_S} cx="32" cy="32" r="22"/><circle {_S} cx="32" cy="32" r="8"/><path {_S} d="M32 10a22 22 0 0 1 22 22M50 46l10 10"/>',
    "tools": f'<path {_S} d="M8 30q0-8 10-8h28q10 0 10 8v4q0 10-12 10t-12-8q0 8-12 8t-12-10zM32 30v6"/>',
}
_FALLBACK = f'<rect {_S} x="12" y="16" width="40" height="34" rx="4"/><path {_S} d="M12 26h40M28 16v10"/>'


@lru_cache(maxsize=1)
def gear() -> dict:
    return json.loads(GEAR.read_text())


def _icon(cat_id: str) -> str:
    return f'<svg viewBox="0 0 64 64" aria-hidden="true">{ICONS.get(cat_id, _FALLBACK)}</svg>'


def _by_id() -> dict:
    return {it["id"]: (c["id"], it) for c in gear()["categories"] for it in c["items"]}


def links_by_key() -> dict[str, list[dict]]:
    """Shopping-list key (e.g. "608_bearing") -> affiliate links, for the
    report's "What else you need" table."""
    g, out = gear(), {}
    for c in g["categories"]:
        for it in c["items"]:
            for k in it.get("keys", []):
                out.setdefault(k, []).append({"name": it["name"], "url": amazon_url(it, g.get("storeId", ""))})
    return out


def apps_nav(current: str = "trebuchet") -> str:
    """The links to both builders, shared with the designer page's header."""
    def a(name, url, key):
        cur = ' aria-current="page" class="cur"' if key == current else ""
        return f'<a href="{url}"{cur}>{name}</a>'
    return a("Rocket Builder", ROCKET_URL, "rocket") + a("Trebuchet Builder", TREBUCHET_URL, "trebuchet")


def _link(item: dict, store: str, inner: str) -> str:
    return f'<a href="{escape(amazon_url(item, store))}" target="_blank" rel="sponsored noopener">{inner}</a>'


def _starter_kit(store: str) -> str:
    kit = gear().get("starterKit")
    if not kit:
        return ""
    items, rows = _by_id(), []
    for n, k in enumerate(kit["items"], 1):
        cat, it = items[k["ref"]]
        rows.append("<li>" + _link(it, store,
                    f'<span class="num">{n}</span><span class="pic">{_icon(cat)}</span>'
                    f'<span class="txt"><strong>{escape(it["name"])}</strong><span class="note">{escape(k["why"])}</span>'
                    f'<span class="cta">Find on Amazon ↗</span></span>') + "</li>")
    return (f'<section class="kit" id="starter-kit"><h2>{escape(kit["title"])}</h2><p>{escape(kit["intro"])}</p>'
            f'<ol class="kitlist">{"".join(rows)}</ol><p class="kitnote">The full list below adds projectiles, '
            f'filament and a tape to measure your throws.</p></section>')


def page() -> str:
    g = gear()
    store = g.get("storeId", "")
    toc = "".join(f'<a href="#{escape(c["id"])}">{escape(c["title"])}</a>' for c in g["categories"])
    sections = []
    for c in g["categories"]:
        cards = []
        for it in c["items"]:
            pic = (f'<img src="{escape(it["photo"])}" alt="" loading="lazy">' if it.get("photo") else _icon(c["id"]))
            cards.append("<li>" + _link(it, store,
                         f'<span class="pic">{pic}</span><span class="txt">'
                         + ('<span class="tag">Start here</span>' if it.get("pick") else "")
                         + f'<strong>{escape(it["name"])}</strong><span class="note">{escape(it["note"])}</span>'
                         f'<span class="cta">{"View" if it.get("asin") else "Find"} on Amazon ↗</span></span>') + "</li>")
        sections.append(f'<section id="{escape(c["id"])}"><h2><span class="hicon">{_icon(c["id"])}</span>{escape(c["title"])}</h2>'
                        f'<p>{escape(c["intro"])}</p><ul class="items">{"".join(cards)}</ul></section>')
    return (_PAGE.replace("{{APPS}}", apps_nav()).replace("{{KIT}}", _starter_kit(store)).replace("{{TOC}}", toc)
            .replace("{{SECTIONS}}", "".join(sections)).replace("{{DISCLOSURE}}", DISCLOSURE))


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="icon" href="data:,">
<title>Order Trebuchet Supplies · Trebuchet Builder</title>
<meta name="description" content="Bearings, bolts, screws, sling cord, counterweight fill, projectiles and filament for the 3D-printed desk trebuchet from Trebuchet Builder.">
<style>
  :root { color-scheme:light; --bg:#fff; --card:#f5f5f7; --ink:#1d1d1f; --muted:#6e6e73; --line:#e5e5ea; --accent:#0a58ca; --warn:#9a6700; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme=light]) { color-scheme:dark; --bg:#111113; --card:#1c1c1f; --ink:#f2f2f4; --muted:#a1a1a6; --line:#2c2c30; --accent:#6ea8fe; --warn:#e3b341; } }
  :root[data-theme=dark] { color-scheme:dark; --bg:#111113; --card:#1c1c1f; --ink:#f2f2f4; --muted:#a1a1a6; --line:#2c2c30; --accent:#6ea8fe; --warn:#e3b341; }
  * { box-sizing:border-box; }
  html { -webkit-text-size-adjust:100%; scroll-behavior:smooth; }
  body { margin:0; font:16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; color:var(--ink); background:var(--bg); }
  a { color:var(--accent); }
  header { display:flex; align-items:center; flex-wrap:wrap; gap:6px 18px; min-height:52px;
    padding:calc(8px + env(safe-area-inset-top, 0px)) 16px 8px; border-bottom:1px solid var(--line); }
  header .brand { font-size:1.15rem; font-weight:700; letter-spacing:.02em; }
  header .brand a { color:var(--ink); text-decoration:none; }
  header nav { display:flex; flex-wrap:wrap; gap:6px 18px; font-size:15px; }
  header nav a { color:var(--ink); text-decoration:none; }
  header nav a:hover { text-decoration:underline; text-underline-offset:5px; }
  header nav.apps { padding:2px; border:1px solid var(--line); border-radius:8px; gap:2px; }
  header nav.apps a { padding:3px 10px; border-radius:6px; font-weight:600; font-size:14px; }
  header nav.apps a.cur { background:var(--ink); color:var(--bg); }
  header nav.apps a:hover { text-decoration:none; }
  header nav.apps a:not(.cur):hover { background:var(--card); }
  main { max-width:1000px; margin:0 auto; padding:24px 16px 64px; }
  main h1 { font-size:clamp(1.6rem, 6vw, 2.2rem); margin:0 0 .25rem; }
  .lede { font-size:1.1rem; color:var(--muted); margin:.25rem 0 1rem; }
  .notice { background:var(--card); border-left:4px solid var(--accent); border-radius:6px; padding:12px 14px; margin:12px 0; }
  .notice small { display:block; color:var(--muted); margin-top:4px; }
  .toc { display:flex; flex-wrap:wrap; gap:6px 8px; margin:18px 0 8px; }
  .toc a { font-size:.9rem; border:1px solid var(--line); border-radius:999px; padding:3px 12px; text-decoration:none; color:var(--ink); }
  .toc a:hover { border-color:var(--accent); }
  section { scroll-margin-top:12px; margin-top:28px; }
  h2 { display:flex; align-items:center; gap:10px; font-size:1.3rem; margin:0 0 4px; }
  h2 .hicon svg { width:30px; height:30px; display:block; color:var(--accent); }
  section > p { margin:0 0 12px; color:var(--muted); }
  .items { list-style:none; padding:0; margin:0; display:grid; grid-template-columns:repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap:12px; }
  .items a { display:grid; grid-template-columns:84px 1fr; gap:14px; align-items:start; height:100%; padding:12px; border:1px solid var(--line);
    border-radius:10px; color:var(--ink); text-decoration:none; transition:border-color .15s, transform .15s; }
  .items a:hover { border-color:var(--accent); transform:translateY(-1px); }
  .pic { display:grid; place-items:center; width:84px; height:84px; border-radius:8px; background:var(--card); overflow:hidden; color:var(--muted); }
  .pic svg { width:52px; height:52px; }
  .pic img { width:100%; height:100%; object-fit:cover; }
  .txt { display:flex; flex-direction:column; gap:4px; min-width:0; }
  .txt strong { font-size:.98rem; line-height:1.35; }
  .note { color:var(--muted); font-size:.92rem; line-height:1.45; }
  .cta { color:var(--accent); font-size:.9rem; font-weight:600; margin-top:2px; }
  .tag { align-self:flex-start; font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--accent);
    border:1px solid var(--accent); border-radius:999px; padding:0 8px; }
  .kit { margin:22px 0 8px; padding:18px 18px 10px; border:2px solid var(--accent); border-radius:12px; }
  .kit h2 { margin:0 0 2px; }
  .kitlist { list-style:none; padding:0; margin:12px 0 4px; display:grid; gap:10px; }
  .kitlist a { display:grid; grid-template-columns:28px 64px 1fr; gap:12px; align-items:center; padding:10px; border:1px solid var(--line);
    border-radius:10px; color:var(--ink); text-decoration:none; background:var(--bg); transition:border-color .15s; }
  .kitlist a:hover { border-color:var(--accent); }
  .kitlist .num { display:grid; place-items:center; width:28px; height:28px; border-radius:50%; background:var(--ink); color:var(--bg); font-weight:700; font-size:.9rem; }
  .kitlist .pic { width:64px; height:64px; } .kitlist .pic svg { width:40px; height:40px; }
  .kitnote { color:var(--muted); font-size:.9rem; }
  footer { border-top:1px solid var(--line); color:var(--muted); font-size:.9rem; padding:20px 16px 32px; text-align:center; }
  @media (max-width:480px) { .kitlist a { grid-template-columns:24px 48px 1fr; } .kitlist .pic { width:48px; height:48px; } .kitlist .pic svg { width:32px; height:32px; }
    .items a { grid-template-columns:64px 1fr; } .pic { width:64px; height:64px; } .pic svg { width:40px; height:40px; } }
</style>
<script>try { const t = localStorage.getItem('theme'); if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t; } catch {}</script>
</head>
<body>
<header><div class="brand"><a href="./">Trebuchet Builder</a></div><nav class="apps" aria-label="Builders">{{APPS}}</nav><nav><a href="./">← Back to the designer</a><a href="https://quiverdesignworks.net">Quiver Design Works</a></nav></header>
<main>
  <h1>Order trebuchet supplies</h1>
  <p class="lede">Everything you need to build and throw a trebuchet from Trebuchet Builder, apart from the printed parts: bearings, bolts and screws, sling cord, counterweight fill, things to throw, filament and safety glasses. Items marked <b>Start here</b> are what I'd buy first.</p>
  <div class="notice"><b>Ordering through these links supports me and Trebuchet Builder</b>, at no extra cost to you.
    <small>{{DISCLOSURE}} Links open Amazon, where you'll see the current price and choices.</small></div>
  {{KIT}}
  <nav class="toc" aria-label="Categories">{{TOC}}</nav>
  {{SECTIONS}}
</main>
<footer>{{DISCLOSURE}} · <a href="./">Trebuchet Builder</a> by <a href="https://quiverdesignworks.net">Quiver Design Works</a></footer>
</body>
</html>
"""
