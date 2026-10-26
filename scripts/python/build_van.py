#!/usr/bin/env python3
"""
Build the /van section of ethan.dev from Markdown.

Content lives in content/van/**/*.md with YAML frontmatter. Each collection
has a `_index.md` (config + intro); each entry is one Markdown file. Listing
pages are generated from entry metadata, so adding a Markdown file publishes an
entry after a build. No hardcoded card markup.

Routes generated (real static HTML, so deep links / refresh / no-JS all work):
  content/van/index.md               -> /van/index.html            (landing)
  content/van/<coll>/_index.md       -> /van/<coll>/index.html     (collection)
  content/van/<coll>/<slug>.md       -> /van/<coll>/<slug>/index.html (detail)
  content/van/costs/_index.md + expenses.csv -> /van/costs/index.html (table)

Markdown: Python-Markdown + PyMdown Extensions (tables, nested/sane lists,
task lists, <details> toggles, admonition callouts, footnotes, attr_list,
md_in_html) with Pygments highlighting at build time.
"""

import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path

import markdown
import yaml

SITE = "https://ethan.dev"

# ---------------------------------------------------------------------------
# Shared chrome (nav / head / theme) — kept in sync with index.html
# ---------------------------------------------------------------------------

NAV_ITEMS = [
    ("/about", "About"),
    ("/album", "Album"),
    ("/road", "Road"),
    ("/van", "Van"),
    ("/utilities", "Utilities"),
    ("/articles", "Articles"),
]


def nav_html(active_href):
    lis = []
    for href, label in NAV_ITEMS:
        cls = "nav-link active" if href == active_href else "nav-link"
        lis.append(f'<li><a href="{href}" class="{cls}">{label}</a></li>')
    links = "\n                    ".join(lis)
    return f'''<nav>
            <div class="nav-row">
                <ul>
                    {links}
                </ul>
                <div class="theme-toggle">
                    <div id="theme-toggle" class="theme-switch" role="button" tabindex="0" aria-label="Toggle theme" title="Toggle theme">
                        <svg class="switch-icon sun" width="14" height="14" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true"><path d="M256 160c-52.9 0-96 43.1-96 96s43.1 96 96 96 96-43.1 96-96-43.1-96-96-96zm246.4 80.5l-94.7-47.3 33.5-100.4c4.5-13.6-8.4-26.5-21.9-21.9l-100.4 33.5-47.4-94.8c-6.4-12.8-24.6-12.8-31 0l-47.3 94.7L92.7 70.8c-13.6-4.5-26.5 8.4-21.9 21.9l33.5 100.4-94.7 47.4c-12.8 6.4-12.8 24.6 0 31l94.7 47.3-33.5 100.5c-4.5 13.6 8.4 26.5 21.9 21.9l100.4-33.5 47.3 94.7c6.4 12.8 24.6 12.8 31 0l47.3-94.7 100.4 33.5c13.6 4.5 26.5-8.4 21.9-21.9l-33.5-100.4 94.7-47.3c12.8-6.4 12.8-24.6 0-31z"/></svg>
                        <span class="switch-thumb"></span>
                        <svg class="switch-icon moon" width="14" height="14" viewBox="0 0 384 512" fill="currentColor" aria-hidden="true"><path d="M223.5 32C100 32 0 132.3 0 256s100 224 223.5 224c60.6 0 115.5-24.2 155.8-63.4 5-4.9 6.3-12.5 3.1-18.7s-10.1-9.7-17-8.5c-9.8 1.7-19.8 2.6-30.1 2.6-96.9 0-175.5-78.8-175.5-176 0-65.8 36-123.1 89.3-153.3 6.1-3.5 9.2-10.5 7.7-17.3s-7.3-11.9-14.3-12.5c-6.3-.5-12.6-.8-19-.8z"/></svg>
                    </div>
                </div>
            </div>
        </nav>'''


THEME_PRELOAD = '''<script>
        (function() {
            try {
                var saved = localStorage.getItem('theme');
                var root = document.documentElement;
                root.classList.remove('theme-light', 'theme-dark');
                if (saved === 'light' || saved === 'dark') { root.classList.add('theme-' + saved); }
            } catch (e) {}
        })();
    </script>'''

THEME_TOGGLE = '''<script>
        (function() {
            const root = document.documentElement;
            const prefersLight = window.matchMedia('(prefers-color-scheme: light)');
            function currentExplicitTheme() { try { return localStorage.getItem('theme'); } catch (_) { return null; } }
            function applyTheme(theme) {
                root.classList.remove('theme-light', 'theme-dark');
                if (theme === 'light' || theme === 'dark') { root.classList.add('theme-' + theme); }
                updateThemeToggleState();
            }
            function updateThemeToggleState() {
                const sw = document.getElementById('theme-toggle');
                if (!sw) return;
                const isLight = !root.classList.contains('theme-dark');
                sw.setAttribute('aria-pressed', String(isLight));
            }
            function toggleTheme() {
                const explicit = currentExplicitTheme();
                const currentIsLight = explicit ? explicit === 'light' : true;
                applyTheme(currentIsLight ? 'dark' : 'light');
            }
            window.addEventListener('DOMContentLoaded', () => {
                const btn = document.getElementById('theme-toggle');
                if (btn && !btn.dataset.bound) {
                    btn.dataset.bound = '1';
                    btn.addEventListener('click', toggleTheme);
                    btn.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleTheme(); } });
                    updateThemeToggleState();
                }
            });
        })();
    </script>'''


def md_parser():
    return markdown.Markdown(
        extensions=[
            "extra", "sane_lists", "toc", "admonition", "attr_list",
            "pymdownx.tasklist", "pymdownx.details", "pymdownx.superfences",
            "pymdownx.highlight", "pymdownx.betterem", "pymdownx.magiclink",
            "pymdownx.smartsymbols",
        ],
        extension_configs={
            "pymdownx.tasklist": {"custom_checkbox": True},
            "pymdownx.highlight": {"use_pygments": True, "guess_lang": False},
            "toc": {"permalink": False},
        },
        output_format="html5",
    )


def render_markdown(text):
    md = md_parser()
    return md.convert(text or "")


# ---------------------------------------------------------------------------
# Content model
# ---------------------------------------------------------------------------

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def parse_doc(path: Path):
    raw = path.read_text(encoding="utf-8")
    m = FM_RE.match(raw)
    if not m:
        return {}, raw
    meta = yaml.safe_load(m.group(1)) or {}
    return meta, m.group(2)


def fmt_date(value):
    if not value:
        return ""
    s = str(value)
    for f in ("%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y"):
        try:
            return datetime.strptime(s, f).strftime("%B %Y")
        except ValueError:
            continue
    return s


def esc(s):
    return html.escape(str(s or ""), quote=True)


# ---------------------------------------------------------------------------
# Page shell
# ---------------------------------------------------------------------------

def page_shell(*, title, description, canonical, active_href, body,
               og_type="website", image=None, jsonld=None, extra_css=True):
    img_tag = f'\n    <meta property="og:image" content="{esc(image)}">' if image else ""
    tw_card = "summary_large_image" if image else "summary"
    tw_img = f'\n    <meta name="twitter:image" content="{esc(image)}">' if image else ""
    jsonld_tag = ""
    if jsonld:
        jsonld_tag = ('\n    <script type="application/ld+json">\n'
                      + json.dumps(jsonld, ensure_ascii=True, indent=2)
                      + "\n    </script>")
    css_links = (
        '<link rel="stylesheet" href="/styles.css">\n'
        '    <link rel="stylesheet" href="/articles.css">\n'
        '    <link rel="stylesheet" href="/van.css">'
    )
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}">
    <link rel="canonical" href="{esc(canonical)}">
    <meta property="og:type" content="{esc(og_type)}">
    <meta property="og:title" content="{esc(title)}">
    <meta property="og:description" content="{esc(description)}">
    <meta property="og:url" content="{esc(canonical)}">{img_tag}
    <meta name="twitter:card" content="{tw_card}">
    <meta name="twitter:title" content="{esc(title)}">
    <meta name="twitter:description" content="{esc(description)}">{tw_img}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preconnect" href="https://diyjmz7hrjx3w.cloudfront.net">
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,700;1,400&family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
    {css_links}
    <link rel="icon" href="/images/favicon.ico" type="image/x-icon">
    {THEME_PRELOAD}{jsonld_tag}
</head>
<body>
    <div class="container">
        {nav_html(active_href)}
        <main class="van">
{body}
        </main>
        <div class="footer">me (at) ethan (dot) dev</div>
    </div>
    {THEME_TOGGLE}
</body>
</html>
'''


# ---------------------------------------------------------------------------
# Image helpers (responsive <img> with dimensions to avoid CLS)
# ---------------------------------------------------------------------------

def img_tag(src, alt="", *, width=None, height=None, cls=None, lazy=True, sizes=None):
    if not src:
        return ""
    attrs = [f'src="{esc(src)}"', f'alt="{esc(alt)}"']
    if width:
        attrs.append(f'width="{int(width)}"')
    if height:
        attrs.append(f'height="{int(height)}"')
    if cls:
        attrs.append(f'class="{esc(cls)}"')
    attrs.append('loading="lazy" decoding="async"' if lazy else 'decoding="async"')
    if sizes:
        attrs.append(f'sizes="{esc(sizes)}"')
    return f'<img {" ".join(attrs)}>'


# ---------------------------------------------------------------------------
# Collection loading
# ---------------------------------------------------------------------------

def load_collection(coll_dir: Path):
    """Return (config_meta, intro_html, [entries]) for a collection directory."""
    cfg_path = coll_dir / "_index.md"
    cfg, intro_md = ({}, "")
    if cfg_path.exists():
        cfg, intro_md = parse_doc(cfg_path)
    entries = []
    for p in sorted(coll_dir.glob("*.md")):
        if p.name.startswith("_"):
            continue
        meta, body = parse_doc(p)
        meta.setdefault("slug", p.stem)
        meta["_body"] = body
        meta["_path"] = p
        entries.append(meta)
    # sort
    sort_key = (cfg.get("sort") or "order")
    reverse = sort_key.startswith("-")
    key = sort_key.lstrip("-")

    def sk(e):
        v = e.get(key)
        if v is None:
            return (1, "")
        return (0, v)
    entries.sort(key=sk, reverse=reverse)
    return cfg, render_markdown(intro_md), entries


# ---------------------------------------------------------------------------
# Renderers per layout
# ---------------------------------------------------------------------------

def chips(entry):
    out = []
    status = entry.get("status")
    if status:
        out.append(f'<span class="van-chip van-status van-status-{esc(status)}">{esc(status)}</span>')
    if entry.get("duration_hours") is not None:
        out.append(f'<span class="van-chip">{esc(entry["duration_hours"])} h</span>')
    if entry.get("date"):
        out.append(f'<span class="van-chip">{esc(fmt_date(entry["date"]))}</span>')
    for t in (entry.get("tags") or []):
        out.append(f'<span class="van-tag">{esc(t)}</span>')
    return f'<div class="van-chips">{"".join(out)}</div>' if out else ""


def card(entry, coll):
    href = f'/van/{coll}/{entry["slug"]}'
    cover = entry.get("cover")
    cover_html = ""
    if cover:
        cover_html = f'<div class="van-card-media">{img_tag(cover, entry.get("title", ""), cls="van-card-img")}</div>'
    rating = entry.get("rating")
    rating_html = f'<span class="van-rating" aria-label="{esc(rating)} out of 5">{"★" * int(rating)}{"☆" * (5 - int(rating))}</span>' if rating else ""
    desc = entry.get("description", "")
    meta_line = chips(entry)
    return f'''<a class="van-card" href="{esc(href)}">
    {cover_html}
    <div class="van-card-body">
        <h3 class="van-card-title">{esc(entry.get("title", entry["slug"]))} {rating_html}</h3>
        {f'<p class="van-card-desc">{esc(desc)}</p>' if desc else ''}
        {meta_line}
    </div>
</a>'''


def render_collection_page(coll, cfg, intro_html, entries, out_root: Path):
    layout = cfg.get("layout", "gallery")
    title = cfg.get("title", coll.title())
    description = cfg.get("description", f"{title} — Van, ethan.dev")
    canonical = f"{SITE}/van/{coll}"
    grid_cls = "van-grid van-grid-journal" if layout == "journal" else "van-grid"
    cards = "\n".join(card(e, coll) for e in entries)
    if not cards:
        cards = '<p class="van-empty">Nothing here yet.</p>'
    body = f'''            <header class="van-header">
                <p class="van-eyebrow"><a href="/van">Van</a></p>
                <h1>{esc(title)}</h1>
                <div class="van-intro">{intro_html}</div>
            </header>
            <section class="{grid_cls}">
{cards}
            </section>'''
    jsonld = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": title, "description": description, "url": canonical,
    }
    out = out_root / "van" / coll / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_shell(title=f"{title} — Van", description=description,
                              canonical=canonical, active_href="/van", body=body,
                              image=entries[0].get("cover") if entries else None,
                              jsonld=jsonld), encoding="utf-8")
    return out


def render_detail_page(coll, cfg, entry, out_root: Path):
    title = entry.get("title", entry["slug"])
    description = entry.get("description", "")
    canonical = f"{SITE}/van/{coll}/{entry['slug']}"
    cover = entry.get("cover")
    cover_html = ""
    if cover:
        cover_html = f'<figure class="van-cover">{img_tag(cover, title, lazy=False)}</figure>'
    rating = entry.get("rating")
    rating_html = f'<div class="van-rating van-rating-lg" aria-label="{esc(rating)} out of 5">{"★" * int(rating)}{"☆" * (5 - int(rating))}</div>' if rating else ""
    source = entry.get("source_url")
    source_html = f'<p class="van-source">Originally published at <a href="{esc(source)}" target="_blank" rel="noopener">{esc(source)}</a></p>' if source else ""
    body_html = render_markdown(entry["_body"])
    coll_title = cfg.get("title", coll.title())
    body = f'''            <article class="van-detail">
                <header class="van-header">
                    <p class="van-eyebrow"><a href="/van">Van</a> / <a href="/van/{coll}">{esc(coll_title)}</a></p>
                    <h1>{esc(title)}</h1>
                    {chips(entry)}
                    {rating_html}
                </header>
                {cover_html}
                <div class="van-prose">
                    {body_html}
                </div>
                {source_html}
                <p class="van-back"><a href="/van/{coll}">← All {esc(coll_title)}</a></p>
            </article>'''
    jsonld = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": title, "description": description, "url": canonical,
        "author": {"@type": "Person", "name": "Ethan Steininger", "url": SITE},
    }
    if entry.get("date"):
        jsonld["datePublished"] = str(entry["date"])
    out = out_root / "van" / coll / entry["slug"] / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_shell(title=f"{title} — Van", description=description,
                              canonical=canonical, active_href="/van", body=body,
                              og_type="article", image=cover, jsonld=jsonld),
                   encoding="utf-8")
    return out


def render_costs_page(coll_dir: Path, out_root: Path):
    cfg, intro_html, _ = load_collection(coll_dir)
    csv_path = coll_dir / "expenses.csv"
    rows = []
    if csv_path.exists():
        with csv_path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append(r)
    # compute subtotals by category + grand total
    def price(r):
        try:
            return float(str(r.get("price", "")).replace("$", "").replace(",", "") or 0)
        except ValueError:
            return 0.0
    cats = {}
    grand = 0.0
    for r in rows:
        c = r.get("category", "Other") or "Other"
        cats.setdefault(c, 0.0)
        cats[c] += price(r)
        grand += price(r)

    def money(v):
        return "${:,.0f}".format(v)

    body_rows = []
    for c in sorted(cats):
        body_rows.append(f'<tr class="van-cost-cat"><th colspan="3">{esc(c)}</th><td class="van-num">{money(cats[c])}</td></tr>')
        for r in [x for x in rows if (x.get("category") or "Other") == c]:
            name = esc(r.get("item", ""))
            link = r.get("link") or r.get("source") or ""
            if link:
                name = f'<a href="{esc(link)}" target="_blank" rel="noopener">{name}</a>'
            body_rows.append(
                f'<tr><td>{name}</td><td class="van-cost-note">{esc(r.get("note",""))}</td>'
                f'<td></td><td class="van-num">{money(price(r))}</td></tr>')
    table = f'''<table class="van-cost-table">
    <thead><tr><th>Item</th><th>Notes</th><th></th><th class="van-num">Price</th></tr></thead>
    <tbody>
    {"".join(body_rows)}
    </tbody>
    <tfoot><tr class="van-cost-total"><th colspan="3">Total</th><td class="van-num">{money(grand)}</td></tr></tfoot>
    </table>''' if rows else '<p class="van-empty">Cost data coming soon.</p>'
    title = cfg.get("title", "Costs")
    description = cfg.get("description", "What the van build cost, itemized.")
    canonical = f"{SITE}/van/costs"
    body = f'''            <header class="van-header">
                <p class="van-eyebrow"><a href="/van">Van</a></p>
                <h1>{esc(title)}</h1>
                <div class="van-intro">{intro_html}</div>
            </header>
            <section class="van-costs">
                {table}
            </section>'''
    out = out_root / "van" / "costs" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_shell(title=f"{title} — Van", description=description,
                              canonical=canonical, active_href="/van", body=body),
                   encoding="utf-8")
    return out, grand


def render_landing(content_root: Path, out_root: Path, collections):
    cfg, body_md = parse_doc(content_root / "index.md")
    intro_html = render_markdown(body_md)
    title = cfg.get("title", "Van")
    description = cfg.get("description", "A self-converted Ford Transit, and traveling while working remotely.")
    canonical = f"{SITE}/van"
    before = cfg.get("before_image")
    after = cfg.get("after_image")
    ba = ""
    if before and after:
        ba = f'''<div class="van-beforeafter">
                    <figure>{img_tag(before, "Before the conversion", lazy=False)}<figcaption>Before</figcaption></figure>
                    <figure>{img_tag(after, "After the conversion", lazy=False)}<figcaption>After</figcaption></figure>
                </div>'''
    video = cfg.get("video_url")
    video_html = ""
    if video:
        video_html = f'''<details class="van-video">
                    <summary>Watch the tour</summary>
                    <div class="van-video-frame"><iframe src="{esc(video)}" title="Van tour" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade"></iframe></div>
                </details>'''
    # section cards from collections config
    sec_cards = []
    for coll, meta in collections:
        href = f"/van/{coll}"
        cov = meta.get("cover")
        cov_html = f'<div class="van-card-media">{img_tag(cov, meta.get("title",""), cls="van-card-img")}</div>' if cov else ""
        sec_cards.append(f'''<a class="van-card van-section-card" href="{esc(href)}">
    {cov_html}
    <div class="van-card-body">
        <h3 class="van-card-title">{esc(meta.get("title", coll.title()))}</h3>
        {f'<p class="van-card-desc">{esc(meta.get("blurb") or meta.get("description",""))}</p>' if (meta.get("blurb") or meta.get("description")) else ''}
    </div>
</a>''')
    body = f'''            <header class="van-header van-landing-header">
                <h1>{esc(title)}</h1>
                <div class="van-intro van-lede">{intro_html}</div>
                {ba}
                {video_html}
            </header>
            <section class="van-grid van-sections">
{"".join(sec_cards)}
            </section>'''
    jsonld = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "Van", "description": description, "url": canonical,
    }
    out = out_root / "van" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_shell(title="Van — Ethan Steininger", description=description,
                              canonical=canonical, active_href="/van", body=body,
                              image=after or cfg.get("cover"), jsonld=jsonld),
                   encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

COLLECTION_ORDER = ["build", "nature", "towns", "resources", "notes"]


def main():
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent.parent
    content_root = root / "content" / "van"
    out_root = root

    if not content_root.exists():
        print(f"no content at {content_root}")
        return

    # rebuild the /van output tree from scratch so renamed/removed entries don't linger
    import shutil
    shutil.rmtree(out_root / "van", ignore_errors=True)

    built = []
    collections_meta = []

    # Collections with entries
    for coll in COLLECTION_ORDER:
        cdir = content_root / coll
        if not cdir.exists():
            continue
        cfg, intro_html, entries = load_collection(cdir)
        if not cfg.get("cover"):
            nxt = next((e.get("cover") for e in entries if e.get("cover")), None)
            if nxt:
                cfg["cover"] = nxt
        collections_meta.append((coll, cfg))
        built.append(render_collection_page(coll, cfg, intro_html, entries, out_root))
        for e in entries:
            built.append(render_detail_page(coll, cfg, e, out_root))

    # Costs (table) — placed after build in the section list
    costs_dir = content_root / "costs"
    grand = None
    if costs_dir.exists():
        cfg_costs, _, _ = load_collection(costs_dir)
        out, grand = render_costs_page(costs_dir, out_root)
        built.append(out)
        # insert costs into section list right after build
        idx = next((i for i, (c, _) in enumerate(collections_meta) if c == "build"), -1)
        collections_meta.insert(idx + 1, ("costs", cfg_costs))

    # Landing
    built.append(render_landing(content_root, out_root, collections_meta))

    print(f"Van build: {len(built)} pages")
    for b in built:
        print("  ✓", b.relative_to(out_root))
    if grand is not None:
        print(f"  costs total: ${grand:,.0f}")


if __name__ == "__main__":
    main()
