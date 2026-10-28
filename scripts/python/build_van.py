#!/usr/bin/env python3
"""
Build the /van section of ethan.dev from Markdown.

The information architecture mirrors the original Notion site (vanlifecoder.com):
a landing page with a hero, before/after, a video tour, a two-column
"Follow Along" / "Documentation" index, and the Build Journal gallery inline.
Sub-pages are reached the same way they were on Notion, with breadcrumbs.

Routes generated (real static HTML, so deep links / refresh / no-JS all work):
  content/van/index.md               -> /van/index.html              (landing)
  content/van/<coll>/_index.md       -> /van/<coll>/index.html       (collection)
  content/van/<coll>/<slug>.md       -> /van/<coll>/<slug>/index.html (detail)
  content/van/routes.md (+ routes/)  -> /van/routes/index.html       (past routes)
  content/van/costs/_index.md + csv  -> /van/costs/index.html        (cost breakdown)
  content/van/prep.md                -> /van/prep/index.html         (single page)
  content/van/misc.md                -> /van/misc/index.html         (single page)
  content/van/lanscapes.md           -> /van/lanscapes/index.html    (single page)
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
# Global ethan.dev chrome (nav / head / theme) — kept in sync with index.html
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


VAN_LIGHTBOX = '''<script>
        (function() {
            var sel = '.van-prose img, .van-cover img, .van-beforeafter img, .van-hero-cover img, img.van-route-map';
            var imgs = Array.prototype.slice.call(document.querySelectorAll(sel));
            if (!imgs.length) return;
            var lb = document.getElementById('van-lb');
            var lbImg = lb.querySelector('.van-lb-img');
            var cur = 0;
            imgs.forEach(function(im, i) {
                im.style.cursor = 'zoom-in';
                im.addEventListener('click', function(e) { e.preventDefault(); open(i); });
            });
            function show(i) {
                cur = (i + imgs.length) % imgs.length;
                var src = imgs[cur].currentSrc || imgs[cur].src;
                lbImg.src = src; lbImg.alt = imgs[cur].alt || '';
            }
            function open(i) { lb.classList.add('is-open'); lb.setAttribute('aria-hidden', 'false'); document.body.style.overflow = 'hidden'; show(i); }
            function close() { lb.classList.remove('is-open'); lb.setAttribute('aria-hidden', 'true'); document.body.style.overflow = ''; lbImg.removeAttribute('src'); }
            lb.querySelector('.van-lb-close').addEventListener('click', close);
            lb.querySelector('.van-lb-next').addEventListener('click', function(e) { e.stopPropagation(); show(cur + 1); });
            lb.querySelector('.van-lb-prev').addEventListener('click', function(e) { e.stopPropagation(); show(cur - 1); });
            lb.addEventListener('click', function(e) { if (e.target === lb || e.target === lbImg) close(); });
            document.addEventListener('keydown', function(e) {
                if (!lb.classList.contains('is-open')) return;
                if (e.key === 'Escape') close();
                else if (e.key === 'ArrowRight') show(cur + 1);
                else if (e.key === 'ArrowLeft') show(cur - 1);
            });
            if (imgs.length < 2) { lb.querySelector('.van-lb-next').style.display = 'none'; lb.querySelector('.van-lb-prev').style.display = 'none'; }
        })();
    </script>'''

LIGHTBOX_MARKUP = '''<div class="van-lb" id="van-lb" aria-hidden="true" role="dialog" aria-label="Image viewer">
        <button class="van-lb-close" type="button" aria-label="Close">✕</button>
        <button class="van-lb-nav van-lb-prev" type="button" aria-label="Previous">‹</button>
        <img class="van-lb-img" alt="">
        <button class="van-lb-nav van-lb-next" type="button" aria-label="Next">›</button>
    </div>'''


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
    return md_parser().convert(text or "")


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


DOC_SVG = ('<svg class="van-card-ico" width="13" height="13" viewBox="0 0 24 24" '
           'fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">'
           '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
           '<path d="M14 3v5h5"/></svg>')


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")


def first_text(body, n=150):
    """A short text preview of a Markdown body, markdown stripped."""
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body or "")       # images
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)            # links -> text
    t = re.sub(r"[#>*_`~\-]", "", t)                          # markers
    t = re.sub(r"\s+", " ", t).strip()
    return (t[: n - 1] + "…") if len(t) > n else t


# ---------------------------------------------------------------------------
# Page shell
# ---------------------------------------------------------------------------

def page_shell(*, title, description, canonical, body,
               og_type="website", image=None, jsonld=None):
    img_tag_ = f'\n    <meta property="og:image" content="{esc(image)}">' if image else ""
    tw_card = "summary_large_image" if image else "summary"
    tw_img = f'\n    <meta name="twitter:image" content="{esc(image)}">' if image else ""
    jsonld_tag = ""
    if jsonld:
        jsonld_tag = ('\n    <script type="application/ld+json">\n'
                      + json.dumps(jsonld, ensure_ascii=True, indent=2)
                      + "\n    </script>")
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
    <meta property="og:url" content="{esc(canonical)}">{img_tag_}
    <meta name="twitter:card" content="{tw_card}">
    <meta name="twitter:title" content="{esc(title)}">
    <meta name="twitter:description" content="{esc(description)}">{tw_img}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preconnect" href="https://diyjmz7hrjx3w.cloudfront.net">
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,700;1,400&family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/styles.css">
    <link rel="stylesheet" href="/articles.css">
    <link rel="stylesheet" href="/van.css">
    <link rel="icon" href="/images/favicon.ico" type="image/x-icon">
    {THEME_PRELOAD}{jsonld_tag}
</head>
<body>
    <div class="container">
        {nav_html("/van")}
        <main class="van">
{body}
        </main>
        <div class="footer">me (at) ethan (dot) dev</div>
    </div>
    {LIGHTBOX_MARKUP}
    {THEME_TOGGLE}
    {VAN_LIGHTBOX}
</body>
</html>
'''


def img_tag(src, alt="", *, width=None, height=None, cls=None, lazy=True):
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
    return f'<img {" ".join(attrs)}>'


# ---------------------------------------------------------------------------
# Breadcrumbs (mirrors Notion: {vanLifeCoder} / Collection / Entry)
# ---------------------------------------------------------------------------

def crumbs(trail):
    """trail: list of (label, href_or_None). Last item renders as current."""
    parts = []
    for i, (label, href) in enumerate(trail):
        last = i == len(trail) - 1
        if href and not last:
            parts.append(f'<a href="{esc(href)}">{esc(label)}</a>')
        else:
            parts.append(f'<span aria-current="page">{esc(label)}</span>')
    sep = ' <span class="van-crumb-sep">/</span> '
    return f'<nav class="van-crumbs" aria-label="Breadcrumb">{sep.join(parts)}</nav>'


# ---------------------------------------------------------------------------
# Collection loading
# ---------------------------------------------------------------------------

def load_collection(coll_dir: Path):
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
# Cards / chips
# ---------------------------------------------------------------------------

def stars(rating):
    try:
        n = int(rating)
    except (TypeError, ValueError):
        return ""
    return ('<span class="van-rating" aria-label="' + esc(f"{n} out of 5") + '">'
            + "★" * n + "☆" * (5 - n) + "</span>")


def status_badge(status):
    if not status:
        return ""
    return (f'<span class="van-badge van-status-{slugify(status)}">{esc(status)}</span>')


def card_meta(entry):
    """The small metadata line under a gallery card (parity with Notion props)."""
    out = []
    st = entry.get("status")
    if st:
        out.append(status_badge(st))
    for t in (entry.get("tags") or ([entry["location"]] if entry.get("location") else [])):
        out.append(f'<span class="van-tag">{esc(t)}</span>')
    dur = entry.get("duration")
    if dur:
        out.append(f'<span class="van-chip">{esc(dur)}</span>')
    if entry.get("date") and entry.get("show_date", True) and not entry.get("status"):
        out.append(f'<span class="van-chip van-chip-date">{esc(fmt_date(entry["date"]))}</span>')
    return f'<div class="van-card-chips">{"".join(out)}</div>' if out else ""


def card(entry, coll):
    href = f'/van/{coll}/{entry["slug"]}'
    cover = entry.get("cover")
    if cover:
        media = f'<div class="van-card-media">{img_tag(cover, entry.get("title", ""), cls="van-card-img")}</div>'
    else:
        preview = esc(entry.get("description") or first_text(entry.get("_body", "")))
        media = f'<div class="van-card-media van-card-textcover"><span>{preview}</span></div>' if preview else '<div class="van-card-media van-card-blank"></div>'
    rating_html = f'<div class="van-card-rating">{stars(entry["rating"])}</div>' if entry.get("rating") else ""
    desc = entry.get("description", "")
    show_desc = desc and not cover is None and coll in ("towns",)  # keep towns blurb; others rely on cover/preview
    title = esc(entry.get("title", entry["slug"]))
    return f'''<a class="van-card" href="{esc(href)}">
    {media}
    <div class="van-card-body">
        <h3 class="van-card-title">{DOC_SVG}{title}</h3>
        {card_meta(entry)}
        {rating_html}
    </div>
</a>'''


def gallery(entries, coll):
    cards = "\n".join(card(e, coll) for e in entries)
    if not cards:
        return '<p class="van-empty">Nothing here yet.</p>'
    return f'<section class="van-grid">\n{cards}\n</section>'


# ---------------------------------------------------------------------------
# Collection & list pages
# ---------------------------------------------------------------------------

def render_collection_page(coll, cfg, intro_html, entries, out_root: Path):
    layout = cfg.get("layout", "gallery")
    title = cfg.get("title", coll.title())
    emoji = cfg.get("emoji", "")
    description = cfg.get("description", f"{title} — Van, ethan.dev")
    canonical = f"{SITE}/van/{coll}"
    view = "List" if layout == "list" else "Gallery"

    if layout == "list":
        rows = []
        for e in entries:
            href = f'/van/{coll}/{e["slug"]}'
            d = esc(e.get("description") or first_text(e.get("_body", ""), 200))
            desc_span = f'<span class="van-listrow-desc">{d}</span>' if d else ""
            rows.append(
                f'<a class="van-listrow" href="{esc(href)}">'
                f'<span class="van-listrow-title">{esc(e.get("title", e["slug"]))}</span>'
                f'{desc_span}</a>')
        listing = (f'<section class="van-list">\n{chr(10).join(rows)}\n</section>'
                   if rows else '<p class="van-empty">Nothing here yet.</p>')
    else:
        listing = gallery(entries, coll)

    body = f'''            {crumbs([("Van", "/van"), (title, None)])}
            <header class="van-header">
                <h1>{(esc(emoji) + " ") if emoji else ""}{esc(title)}</h1>
                <div class="van-intro">{intro_html}</div>
                <div class="van-viewtag">{view} view</div>
            </header>
{listing}'''
    jsonld = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": title, "description": description, "url": canonical,
    }
    out = out_root / "van" / coll / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_shell(title=f"{title} — Van", description=description,
                              canonical=canonical, body=body,
                              image=next((e.get("cover") for e in entries if e.get("cover")), None),
                              jsonld=jsonld), encoding="utf-8")
    return out


def prop_rows(entry):
    """Notion-style property block on a detail page."""
    rows = []

    def row(label, value):
        if value:
            rows.append(f'<div class="van-prop"><span class="van-prop-k">{esc(label)}</span>'
                        f'<span class="van-prop-v">{value}</span></div>')
    if entry.get("status"):
        row("Status", status_badge(entry["status"]))
    if entry.get("category"):
        row("Category", f'<span class="van-tag">{esc(entry["category"])}</span>')
    if entry.get("location"):
        row("Location", f'<span class="van-tag">{esc(entry["location"])}</span>')
    if entry.get("rating"):
        row("Rating", stars(entry["rating"]))
    if entry.get("duration"):
        row("Time", esc(entry["duration"]))
    if entry.get("date"):
        row("Date", esc(fmt_date(entry["date"])))
    return f'<div class="van-props">{"".join(rows)}</div>' if rows else ""


def render_detail_page(coll, cfg, entry, out_root: Path):
    title = entry.get("title", entry["slug"])
    description = entry.get("description") or first_text(entry.get("_body", ""), 150)
    canonical = f"{SITE}/van/{coll}/{entry['slug']}"
    coll_title = cfg.get("title", coll.title())
    cover = entry.get("cover")
    cover_html = f'<figure class="van-cover">{img_tag(cover, title, lazy=False)}</figure>' if cover else ""
    source = entry.get("source_url")
    source_html = (f'<p class="van-source">Originally at <a href="{esc(source)}" target="_blank" rel="noopener">{esc(source)}</a></p>'
                   if source else "")
    body_html = render_markdown(entry["_body"])
    body = f'''            <article class="van-detail">
                {crumbs([("Van", "/van"), (coll_title, f"/van/{coll}"), (title, None)])}
                <header class="van-detail-header">
                    <h1>{esc(title)}</h1>
                    {prop_rows(entry)}
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
                              canonical=canonical, body=body,
                              og_type="article", image=cover, jsonld=jsonld),
                   encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Single markdown pages (Prep, Misc, Lanscapes)
# ---------------------------------------------------------------------------

def render_single_page(name, md_path: Path, out_root: Path):
    cfg, body_md = parse_doc(md_path)
    title = cfg.get("title", name.title())
    emoji = cfg.get("emoji", "")
    description = cfg.get("description", f"{title} — Van, ethan.dev")
    canonical = f"{SITE}/van/{name}"
    body_html = render_markdown(body_md)
    if not body_html.strip():
        body_html = '<p class="van-empty">Nothing here yet.</p>'
    body = f'''            <article class="van-detail">
                {crumbs([("Van", "/van"), (title, None)])}
                <header class="van-detail-header">
                    <h1>{(esc(emoji) + " ") if emoji else ""}{esc(title)}</h1>
                    {f'<p class="van-intro">{esc(cfg["intro"])}</p>' if cfg.get("intro") else ""}
                </header>
                <div class="van-prose">
                    {body_html}
                </div>
                <p class="van-back"><a href="/van">← Back to Van</a></p>
            </article>'''
    out = out_root / "van" / name / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_shell(title=f"{title} — Van", description=description,
                              canonical=canonical, body=body), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Past Routes (maps by year)
# ---------------------------------------------------------------------------

def render_routes_page(content_root: Path, out_root: Path):
    md_path = content_root / "routes.md"
    if not md_path.exists():
        return None
    cfg, _ = parse_doc(md_path)
    title = cfg.get("title", "Past Routes")
    emoji = cfg.get("emoji", "\U0001F5FA️")
    description = cfg.get("description", "Where the van has been, by year.")
    canonical = f"{SITE}/van/routes"
    build_link = cfg.get("build_your_own")
    years = cfg.get("years", [])
    blocks = []
    for y in years:
        img = img_tag(y.get("map"), f'{y.get("year")} route map', cls="van-route-map") if y.get("map") else ""
        states = ", ".join(y.get("states", []))
        note = f'<p class="van-route-note">{esc(y["note"])}</p>' if y.get("note") else ""
        blocks.append(f'''<article class="van-route">
    <div class="van-route-head"><h2>{esc(y.get("year"))}</h2>
    <p class="van-route-states">{esc(states)}</p></div>
    {f'<figure class="van-route-fig">{img}</figure>' if img else ''}
    {note}
</article>''')
    intro = ""
    if build_link:
        intro = (f'<p class="van-intro">Build your own: '
                 f'<a href="{esc(build_link)}" target="_blank" rel="noopener">{esc(build_link)}</a></p>')
    body = f'''            {crumbs([("Van", "/van"), (title, None)])}
            <header class="van-header">
                <h1>{esc(emoji)} {esc(title)}</h1>
                {intro}
            </header>
            <section class="van-routes">
{"".join(blocks)}
            </section>
            <p class="van-back"><a href="/van">← Back to Van</a></p>'''
    out = out_root / "van" / "routes" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_shell(title=f"{title} — Van", description=description,
                              canonical=canonical, body=body,
                              image=years[0].get("map") if years else None),
                   encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Cost Breakdown (from the real Google Sheet export)
# ---------------------------------------------------------------------------

def render_costs_page(coll_dir: Path, out_root: Path):
    cfg, intro_html, _ = load_collection(coll_dir)
    csv_path = coll_dir / "expenses.csv"
    rows = []
    if csv_path.exists():
        with csv_path.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows.append({(k or "").strip(): (v or "").strip() for k, v in r.items()})

    def price(r):
        try:
            return float(str(r.get("Price", r.get("price", ""))).replace("$", "").replace(",", "") or 0)
        except ValueError:
            return 0.0

    def money(v):
        return "${:,.0f}".format(v)

    cats = {}
    items_total = 0.0
    for r in rows:
        c = r.get("Category") or r.get("category") or "Other"
        cats.setdefault(c, [])
        cats[c].append(r)
        items_total += price(r)

    # Headline figures are authoritative from the sheet summary.
    conv = cfg.get("conversion_cost")
    van = cfg.get("van_cost")
    total = cfg.get("total_cost")
    summary = ""
    if conv or van or total:
        cells = []
        if conv:
            cells.append(f'<div class="van-cost-fig"><span class="van-cost-fig-k">Conversion</span><span class="van-cost-fig-v">{esc(conv)}</span></div>')
        if van:
            cells.append(f'<div class="van-cost-fig"><span class="van-cost-fig-k">Van</span><span class="van-cost-fig-v">{esc(van)}</span></div>')
        if total:
            cells.append(f'<div class="van-cost-fig van-cost-fig-total"><span class="van-cost-fig-k">Total</span><span class="van-cost-fig-v">{esc(total)}</span></div>')
        summary = f'<div class="van-cost-summary">{"".join(cells)}</div>'

    body_rows = []
    # Biggest systems first; the uncategorized "Other" bucket always sits last.
    cat_order = sorted(cats, key=lambda c: (c.lower() == "other", -sum(price(r) for r in cats[c])))
    for c in cat_order:
        sub = sum(price(r) for r in cats[c])
        body_rows.append(f'<tr class="van-cost-cat"><th colspan="2">{esc(c)}</th><td class="van-num">{money(sub)}</td></tr>')
        for r in sorted(cats[c], key=price, reverse=True):
            name = esc(r.get("Item") or r.get("item", ""))
            note = esc(r.get("Notes") or r.get("note", ""))
            body_rows.append(
                f'<tr><td>{name}</td><td class="van-cost-note">{note}</td>'
                f'<td class="van-num">{money(price(r))}</td></tr>')
    table = (f'''<table class="van-cost-table">
    <thead><tr><th>Item</th><th>Notes</th><th class="van-num">Price</th></tr></thead>
    <tbody>
    {"".join(body_rows)}
    </tbody>
    <tfoot><tr class="van-cost-total"><th colspan="2">Itemized total</th><td class="van-num">{money(items_total)}</td></tr></tfoot>
    </table>''' if rows else '<p class="van-empty">Cost data coming soon.</p>')

    title = cfg.get("title", "Cost Breakdown")
    emoji = cfg.get("emoji", "")
    description = cfg.get("description", "What the van build cost, itemized.")
    canonical = f"{SITE}/van/costs"
    body = f'''            {crumbs([("Van", "/van"), (title, None)])}
            <header class="van-header">
                <h1>{(esc(emoji) + " ") if emoji else ""}{esc(title)}</h1>
                <div class="van-intro">{intro_html}</div>
            </header>
            {summary}
            <section class="van-costs">
                {table}
            </section>
            <p class="van-back"><a href="/van">← Back to Van</a></p>'''
    out = out_root / "van" / "costs" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_shell(title=f"{title} — Van", description=description,
                              canonical=canonical, body=body), encoding="utf-8")
    return out, total or money(items_total)


# ---------------------------------------------------------------------------
# Landing (mirrors the Notion home: hero, before/after, video, index, journal)
# ---------------------------------------------------------------------------

FOLLOW_ALONG = [
    ("\U0001FAB4", "Nature Reviews", "/van/nature"),
    ("\U0001F3D8️", "Town Rankings", "/van/towns"),
    ("\U0001F5FA️", "Past Routes", "/road"),
    ("\U0001F4F7", "Instagram", "https://instagram.com/vanlifecoder"),
    ("\U0001F4FD️", "YouTube", "https://youtube.com/@vanlifecoder"),
]
DOCUMENTATION = [
    ("\U0001F4C9", "Cost Breakdown", "/van/costs"),
    ("\U0001F4A1", "Vanspiration", "/van/resources"),
    ("\U0001F9F9", "VanLifeCoder Prep", "/van/prep"),
    ("\U0001F4DD", "Misc", "/van/misc"),
]


def link_list(items):
    rows = []
    for emoji, label, href in items:
        ext = href.startswith("http")
        attr = ' target="_blank" rel="noopener"' if ext else ""
        rows.append(f'<a class="van-link" href="{esc(href)}"{attr}>'
                    f'<span class="van-link-emoji">{esc(emoji)}</span>'
                    f'<span class="van-link-label">{esc(label)}</span></a>')
    return "\n".join(rows)


def stories_component(cfg):
    """An Instagram-stories-style carousel: tappable poster bubbles that open a
    viewer which autoplays each clip with progress bars and tap-to-advance."""
    stories = cfg.get("stories") or []
    if not stories:
        return "", ""
    title = cfg.get("stories_title", "Stories")
    bubbles = []
    for i, s in enumerate(stories):
        poster = s.get("poster")
        label = s.get("label", f"Clip {i+1}")
        bubbles.append(
            f'<button class="van-story-bubble" type="button" data-i="{i}" aria-label="Play {esc(label)}">'
            f'<span class="van-story-ring"><span class="van-story-thumb">{img_tag(poster, esc(label), cls="")}</span></span>'
            f'<span class="van-story-cap">{esc(label)}</span></button>')
    section = f'''<section class="van-stories" aria-label="{esc(title)}">
                <h2 class="van-section-title">{esc(title)}</h2>
                <div class="van-stories-row">
                    {"".join(bubbles)}
                </div>
            </section>'''
    data_js = json.dumps([{"src": s.get("src"), "poster": s.get("poster"), "label": s.get("label", f"Clip {i+1}")}
                          for i, s in enumerate(stories)])
    viewer = f'''<div class="van-viewer" id="van-viewer" aria-hidden="true" role="dialog" aria-label="Stories">
            <div class="van-viewer-backdrop" data-close></div>
            <div class="van-viewer-stage">
                <div class="van-viewer-bars" id="van-viewer-bars"></div>
                <div class="van-viewer-top">
                    <span class="van-viewer-title">vanlifecoder</span>
                    <div class="van-viewer-actions">
                        <button class="van-viewer-btn" id="van-viewer-mute" type="button" aria-label="Toggle sound">\U0001F507</button>
                        <button class="van-viewer-btn" data-close type="button" aria-label="Close">✕</button>
                    </div>
                </div>
                <video class="van-viewer-video" id="van-viewer-video" playsinline muted preload="auto"></video>
                <button class="van-viewer-zone van-viewer-prev" id="van-viewer-prev" type="button" aria-label="Previous"></button>
                <button class="van-viewer-zone van-viewer-next" id="van-viewer-next" type="button" aria-label="Next"></button>
            </div>
        </div>
        <script>
        (function() {{
            var STORIES = {data_js};
            if (!STORIES.length) return;
            var viewer = document.getElementById('van-viewer');
            var video = document.getElementById('van-viewer-video');
            var barsEl = document.getElementById('van-viewer-bars');
            var muteBtn = document.getElementById('van-viewer-mute');
            var idx = 0, playing = false;
            STORIES.forEach(function() {{
                var b = document.createElement('span'); b.className = 'van-bar';
                b.innerHTML = '<i></i>'; barsEl.appendChild(b);
            }});
            var bars = barsEl.querySelectorAll('.van-bar i');
            function setBars() {{
                bars.forEach(function(el, i) {{ el.style.width = i < idx ? '100%' : '0%'; }});
            }}
            function preload(i) {{
                if (i >= 0 && i < STORIES.length) {{ var im = new Image(); im.src = STORIES[i].poster; }}
            }}
            function load(i) {{
                idx = i; setBars();
                video.poster = STORIES[i].poster;
                video.src = STORIES[i].src;
                video.currentTime = 0;
                var p = video.play(); if (p && p.catch) p.catch(function() {{}});
                preload(i + 1);
            }}
            function open(i) {{
                viewer.classList.add('is-open'); viewer.setAttribute('aria-hidden', 'false');
                document.body.style.overflow = 'hidden'; playing = true; load(i);
            }}
            function close() {{
                viewer.classList.remove('is-open'); viewer.setAttribute('aria-hidden', 'true');
                document.body.style.overflow = ''; playing = false; video.pause(); video.removeAttribute('src'); video.load();
            }}
            function next() {{ if (idx < STORIES.length - 1) load(idx + 1); else close(); }}
            function prev() {{ if (idx > 0) load(idx - 1); else load(0); }}
            video.addEventListener('timeupdate', function() {{
                if (video.duration) bars[idx].style.width = (100 * video.currentTime / video.duration) + '%';
            }});
            video.addEventListener('ended', next);
            document.getElementById('van-viewer-next').addEventListener('click', next);
            document.getElementById('van-viewer-prev').addEventListener('click', prev);
            muteBtn.addEventListener('click', function() {{
                video.muted = !video.muted;
                muteBtn.textContent = video.muted ? '\U0001F507' : '\U0001F50A';
            }});
            Array.prototype.forEach.call(document.querySelectorAll('[data-close]'), function(el) {{
                el.addEventListener('click', close);
            }});
            document.addEventListener('keydown', function(e) {{
                if (!viewer.classList.contains('is-open')) return;
                if (e.key === 'Escape') close();
                else if (e.key === 'ArrowRight') next();
                else if (e.key === 'ArrowLeft') prev();
            }});
            // pause on hold (pointer down on the stage, not the nav zones)
            video.addEventListener('pointerdown', function() {{ video.pause(); }});
            video.addEventListener('pointerup', function() {{ if (playing) video.play().catch(function(){{}}); }});
            Array.prototype.forEach.call(document.querySelectorAll('.van-story-bubble'), function(b) {{
                b.addEventListener('click', function() {{ open(parseInt(b.getAttribute('data-i'), 10) || 0); }});
                var im = new Image(); im.src = STORIES[parseInt(b.getAttribute('data-i'), 10) || 0].poster;
            }});
        }})();
        </script>'''
    return section, viewer


def routes_strip(out_root: Path) -> str:
    """Compact preview of the real road trips (routes.json), each linking to /road."""
    import json as _json
    from datetime import datetime
    rj = out_root / "routes.json"
    if not rj.exists():
        return ""
    try:
        routes = _json.loads(rj.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(routes, list) or not routes:
        return ""

    def _key(r):
        try:
            return datetime.strptime(r.get("date") or "", "%Y-%m-%d")
        except Exception:
            return datetime.min
    routes = sorted(routes, key=_key, reverse=True)

    cards = []
    for r in routes:
        name = esc(str(r.get("name") or r.get("id") or "Route"))
        img = r.get("image")
        states = r.get("tags") if isinstance(r.get("tags"), list) else []
        meta = ", ".join(states[:3]) + ("…" if len(states) > 3 else "")
        thumb = (f'<img src="{esc(img)}" alt="{name}" loading="lazy" decoding="async">'
                 if img else '<span class="van-route-noimg"></span>')
        states_html = f'<span class="van-route-states">{esc(meta)}</span>' if meta else ''
        cards.append(
            f'<a class="van-route-card" href="/road" aria-label="Past routes: {name}">'
            f'{thumb}<span class="van-route-name">{name}</span>{states_html}</a>'
        )
    return f'''<section class="van-routes-strip">
                <div class="van-routes-strip-head">
                    <h2 class="van-section-title">Past Routes</h2>
                    <a class="van-routes-all" href="/road">See the maps →</a>
                </div>
                <div class="van-route-scroller">
                    {''.join(cards)}
                </div>
            </section>'''


def render_landing(content_root: Path, out_root: Path, build_entries):
    cfg, body_md = parse_doc(content_root / "index.md")
    intro_html = render_markdown(body_md)
    title = cfg.get("title", "Software Developer in a Van")
    description = cfg.get("description", "A self-converted Ford Transit, and working from the road.")
    canonical = f"{SITE}/van"
    cover = cfg.get("cover")
    before = cfg.get("before_image")
    after = cfg.get("after_image")

    cover_html = ""
    if cover:
        cover_html = f'<div class="van-hero-cover">{img_tag(cover, "Illustration of the van", lazy=False)}</div>'

    ba = ""
    if before and after:
        ba = f'''<div class="van-beforeafter">
                    <figure><figcaption>Before</figcaption>{img_tag(before, "Before the conversion", lazy=False)}</figure>
                    <figure><figcaption>After</figcaption>{img_tag(after, "After the conversion", lazy=False)}</figure>
                </div>'''

    video = cfg.get("video_embed")
    video_html = ""
    if video:
        video_html = f'''<details class="van-video">
                    <summary>Video Tour</summary>
                    <div class="van-video-frame van-video-short"><iframe src="{esc(video)}" title="Van tour" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade"></iframe></div>
                </details>'''

    journal = gallery(build_entries, "build")
    routes_html = routes_strip(out_root)
    stories_section, stories_viewer = stories_component(cfg)

    body = f'''            {cover_html}
            <header class="van-header van-landing-header">
                <h1>{esc(title)}</h1>
                <div class="van-intro van-lede">{intro_html}</div>
                {ba}
                {video_html}
            </header>
            {stories_section}
            <section class="van-index">
                <div class="van-col">
                    <h2 class="van-section-title">Follow Along</h2>
                    <div class="van-linklist">
                        {link_list(FOLLOW_ALONG)}
                    </div>
                </div>
                <div class="van-col">
                    <h2 class="van-section-title">Documentation</h2>
                    <div class="van-linklist">
                        {link_list(DOCUMENTATION)}
                    </div>
                </div>
            </section>
            {routes_html}
            <section class="van-journal">
                <h2 class="van-section-title">Build Journal</h2>
                {journal}
            </section>
            {stories_viewer}'''
    jsonld = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "Van", "description": description, "url": canonical,
    }
    out = out_root / "van" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_shell(title="Van — Ethan Steininger", description=description,
                              canonical=canonical, body=body,
                              image=cover or after, jsonld=jsonld), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# coll -> is a gallery/list collection with entries + detail pages
GALLERY_COLLECTIONS = ["build", "nature", "towns", "resources"]
SINGLE_PAGES = ["prep", "misc"]


def main():
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent.parent
    content_root = root / "content" / "van"
    out_root = root

    if not content_root.exists():
        print(f"no content at {content_root}")
        return

    import shutil
    shutil.rmtree(out_root / "van", ignore_errors=True)

    built = []
    build_entries = []

    for coll in GALLERY_COLLECTIONS:
        cdir = content_root / coll
        if not cdir.exists():
            continue
        cfg, intro_html, entries = load_collection(cdir)
        if coll == "build":
            build_entries = entries
        built.append(render_collection_page(coll, cfg, intro_html, entries, out_root))
        for e in entries:
            built.append(render_detail_page(coll, cfg, e, out_root))

    # Past Routes now reuses the real /road page (routes.json). The landing
    # shows a preview strip linking there; no separate /van/routes page.

    # Cost Breakdown
    costs_dir = content_root / "costs"
    if costs_dir.exists():
        out, total = render_costs_page(costs_dir, out_root)
        built.append(out)

    # Single pages
    for name in SINGLE_PAGES:
        p = content_root / f"{name}.md"
        if p.exists():
            built.append(render_single_page(name, p, out_root))

    # Landing
    built.append(render_landing(content_root, out_root, build_entries))

    print(f"Van build: {len(built)} pages")
    for b in built:
        print("  ✓", b.relative_to(out_root))


if __name__ == "__main__":
    main()
