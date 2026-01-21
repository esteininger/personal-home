#!/usr/bin/env python3
"""
Convert markdown posts to standalone HTML article pages.
Reads markdown files from posts/ and generates HTML files in articles/
"""

import json
import re
from html import escape as html_escape
from pathlib import Path
from textwrap import dedent

def parse_frontmatter(content):
    """Extract frontmatter and content from markdown file."""
    frontmatter_pattern = r'^---\n(.*?)\n---\n(.*)$'
    match = re.match(frontmatter_pattern, content, re.DOTALL)
    
    if not match:
        return {}, content
    
    frontmatter_text = match.group(1)
    markdown_content = match.group(2)
    
    metadata = {}
    for line in frontmatter_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            metadata[key] = value
    
    return metadata, markdown_content

def markdown_to_html(markdown):
    """Convert markdown to HTML with basic formatting."""
    html = markdown
    
    # Escape HTML in code blocks first
    def escape_html(text):
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Handle fenced code blocks
    html = re.sub(r'```([\w#+-]*)\n(.*?)```', 
                  lambda m: f'<pre><code class="language-{m.group(1).strip()}">{escape_html(m.group(2))}</code></pre>',
                  html, flags=re.DOTALL)
    
    # Images (MUST be processed BEFORE links!)
    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', 
                  r'<img src="\2" alt="\1" style="max-width: 100%; height: auto; margin: 1rem 0;">', html)
    
    # Links
    html = re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', 
                  r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', html)
    
    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    
    # Bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    
    # Italic
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # Inline code (but not in links)
    html = re.sub(r'`([^`]+?)`', lambda m: f'<code>{escape_html(m.group(1))}</code>', html)
    
    # Lists (unordered and ordered)
    html = re.sub(r'^\* (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    
    # Wrap consecutive list items
    html = re.sub(r'(<li>.*</li>\n?)+', lambda m: f'<ul>{m.group(0)}</ul>', html)
    
    # Paragraphs - split by double newlines and wrap non-tag lines
    paragraphs = html.split('\n\n')
    html_paragraphs = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # Don't wrap if it's already a tag
        if para.startswith('<'):
            html_paragraphs.append(para)
        else:
            html_paragraphs.append(f'<p>{para}</p>')
    
    html = '\n'.join(html_paragraphs)
    
    return html

def create_article_html(post_id, metadata, html_content):
    """Generate full HTML page for an article."""
    title = metadata.get('title', 'Untitled')
    date = metadata.get('date', '')
    description = metadata.get('description', '')

    # Format date
    from datetime import datetime
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%B %d, %Y')
    except:
        formatted_date = date

    # Escape HTML for meta tags
    title_escaped = html_escape(title)
    description_escaped = html_escape(description)
    post_url = f"https://ethan.dev/{post_id}"

    template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ethan - {post_id}</title>
    <meta name="description" content="{description_escaped}">
    <meta property="og:title" content="{title_escaped} - Ethan Steininger">
    <meta property="og:description" content="{description_escaped}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{post_url}">
    <meta property="article:published_time" content="{date}">
    <meta property="article:author" content="Ethan Steininger">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{title_escaped} - Ethan Steininger">
    <meta name="twitter:description" content="{description_escaped}">
    <link rel="canonical" href="{post_url}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
    <link rel="stylesheet" href="/styles.css">
    <link rel="stylesheet" href="/articles.css">
    <script>
        (function() {{
            try {{
                var saved = localStorage.getItem('theme');
                var root = document.documentElement;
                root.classList.remove('theme-light', 'theme-dark');
                if (saved === 'light' || saved === 'dark') {{
                    root.classList.add('theme-' + saved);
                }}
            }} catch (e) {{ /* noop */ }}
        }})();
    </script>
    <link rel="icon" href="/images/favicon.ico" type="image/x-icon">
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "{title_escaped}",
        "description": "{description_escaped}",
        "datePublished": "{date}",
        "author": {{
            "@type": "Person",
            "name": "Ethan Steininger",
            "url": "https://ethan.dev"
        }},
        "publisher": {{
            "@type": "Person",
            "name": "Ethan Steininger"
        }},
        "url": "{post_url}"
    }}
    </script>
</head>
<body>
    <div class="container">
        <nav>
            <div class="nav-row">
                <ul>
                    <li><a href="/about" class="nav-link">About</a></li>
                    <li><a href="/articles" class="nav-link active">Articles</a></li>
                    <li><a href="/album" class="nav-link">Album</a></li>
                    <li><a href="/utilities" class="nav-link">Utilities</a></li>
                </ul>
                <div class="theme-toggle">
                    <div id="theme-toggle" class="theme-switch" role="button" tabindex="0" aria-label="Toggle theme" title="Toggle theme">
                        <i class="fa-solid fa-sun switch-icon sun" aria-hidden="true"></i>
                        <span class="switch-thumb"></span>
                        <i class="fa-solid fa-moon switch-icon moon" aria-hidden="true"></i>
                    </div>
                </div>
            </div>
        </nav>
        <div id="articles" class="page active">
            <div class="blog-post">
                <div class="post-header">
                    <h1>{title}</h1>
                    <div class="post-date">{formatted_date}</div>
                </div>
                <div class="post-content">
                    {html_content}
                </div>
            </div>
        </div>
        <div class="footer">me (at) ethan (dot) dev</div>
    </div>
    <script>
        // Theme handling
        (function() {{
            const root = document.documentElement;
            const prefersLight = window.matchMedia('(prefers-color-scheme: light)');

            function currentExplicitTheme() {{
                try {{ return localStorage.getItem('theme'); }} catch (_) {{ return null; }}
            }}

            function applyTheme(theme) {{
                root.classList.remove('theme-light', 'theme-dark');
                if (theme === 'light' || theme === 'dark') {{
                    root.classList.add('theme-' + theme);
                }}
                updateThemeToggleState();
            }}

            function updateThemeToggleState() {{
                const sw = document.getElementById('theme-toggle');
                if (!sw) return;
                const isLight = root.classList.contains('theme-light') || (!root.classList.contains('theme-dark') && prefersLight.matches);
                sw.setAttribute('aria-pressed', String(isLight));
            }}

            function toggleTheme() {{
                const explicit = currentExplicitTheme();
                let next;
                if (explicit) {{
                    next = explicit === 'light' ? 'dark' : 'light';
                }} else {{
                    next = prefersLight.matches ? 'dark' : 'light';
                }}
                try {{ localStorage.setItem('theme', next); }} catch (_) {{}}
                applyTheme(next);
            }}

            window.addEventListener('DOMContentLoaded', () => {{
                const btn = document.getElementById('theme-toggle');
                if (btn && !btn.dataset.bound) {{
                    btn.dataset.bound = '1';
                    btn.addEventListener('click', toggleTheme);
                    btn.addEventListener('keydown', (e) => {{
                        if (e.key === 'Enter' || e.key === ' ') {{
                            e.preventDefault();
                            toggleTheme();
                        }}
                    }});
                    updateThemeToggleState();
                }}
            }});

            try {{
                prefersLight.addEventListener('change', () => {{
                    if (!currentExplicitTheme()) {{
                        applyTheme(null);
                    }}
                }});
            }} catch (_) {{}}
        }})();
    </script>
</body>
</html>
'''
    return template

def build_utilities_page(project_root: Path):
    """Generate a static utilities index page using shared metadata."""
    utilities_dir = project_root / 'utilities'
    metadata_path = utilities_dir / 'utilities.json'

    if not metadata_path.exists():
        print("utilities/index.html skipped (utilities/utilities.json not found)")
        return

    try:
        data = json.loads(metadata_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        print(f"Failed to parse {metadata_path.name}: {exc}")
        return

    page = data.get('page', {})
    page_meta = page.get('meta', {})
    utilities = data.get('utilities', [])

    title_text = page_meta.get('title') or f"ethan - {page.get('title', 'utilities')}"
    description = page_meta.get('description') or page.get('blurb') or page.get('description') or ''
    canonical = page_meta.get('canonical') or ''
    twitter_card = page_meta.get('twitterCard') or 'summary'
    og_type = page_meta.get('ogType') or 'website'
    headline = page.get('headline') or page.get('title') or 'Utilities'
    blurb = page.get('blurb') or page.get('description') or ''

    cards_html_parts = []
    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": headline,
        "description": description or blurb,
        "itemListElement": []
    }

    for index, utility in enumerate(utilities, start=1):
        slug = str(utility.get('slug', '')).strip('/')
        href_path = f"/utilities/{slug}" if slug else "/utilities"
        utility_name = html_escape(utility.get('name') or slug or 'Utility')
        teaser = html_escape(utility.get('teaser') or utility.get('shortDescription') or '')
        tags = utility.get('tags') or []
        tags_html = ''
        if tags:
            tags_html = ''.join(f'<span class="tag">{html_escape(tag)}</span>' for tag in tags)
            tags_html = f'\n                    <div class="utility-tags">{tags_html}</div>'
        description_html = f'\n                    <p class="utility-description">{teaser}</p>' if teaser else ''

        cards_html_parts.append(
            f'''                <a class="utility-card" href="{html_escape(href_path)}">
                    <h2>{utility_name}</h2>{description_html}{tags_html}
                </a>'''
        )

        utility_meta = utility.get('meta', {}) if isinstance(utility.get('meta'), dict) else {}
        canonical_util = utility_meta.get('canonical')
        if not canonical_util:
            base = canonical.rstrip('/') if canonical else ''
            if base and slug:
                canonical_util = f"{base}/{slug}"
            elif base:
                canonical_util = base
            else:
                canonical_util = href_path

        schema_payload = {}
        if isinstance(utility.get('schema'), dict):
            schema_payload = {k: v for k, v in utility['schema'].items() if k != '@context'}
        schema_payload.setdefault('@type', 'SoftwareApplication')
        if 'name' not in schema_payload:
            schema_payload['name'] = utility.get('name') or ''
        if 'description' not in schema_payload:
            schema_payload['description'] = utility_meta.get('description') or utility.get('shortDescription') or ''
        schema_payload['url'] = utility_meta.get('canonical') or canonical_util

        item_list['itemListElement'].append({
            "@type": "ListItem",
            "position": index,
            "url": canonical_util,
            "name": utility.get('name') or slug or f"Utility {index}",
            "item": schema_payload
        })

    if not cards_html_parts:
        cards_block = '                <p class="utilities-empty">Utilities will be available soon.</p>'
    else:
        cards_block = '\n'.join(cards_html_parts)

    schema_script = ''
    if item_list['itemListElement']:
        schema_json = json.dumps(item_list, ensure_ascii=True, indent=2)
        schema_script = f'\n    <script type="application/ld+json">\n{schema_json}\n    </script>'

    template = dedent(f'''\
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{html_escape(title_text)}</title>
        <meta name="description" content="{html_escape(description)}">
        <meta name="twitter:card" content="{html_escape(twitter_card)}">
        <meta name="twitter:title" content="{html_escape(title_text)}">
        <meta name="twitter:description" content="{html_escape(description)}">
        <meta property="og:type" content="{html_escape(og_type)}">
        <meta property="og:title" content="{html_escape(title_text)}">
        <meta property="og:description" content="{html_escape(description)}">
        {'<meta property="og:url" content="{}">'.format(html_escape(canonical)) if canonical else ''}
        {'<link rel="canonical" href="{}">'.format(html_escape(canonical)) if canonical else ''}
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
        <link rel="stylesheet" href="/styles.css">
        {schema_script}
        <script>
            (function() {{
                try {{
                    var saved = localStorage.getItem('theme');
                    var root = document.documentElement;
                    root.classList.remove('theme-light', 'theme-dark');
                    if (saved === 'light' || saved === 'dark') {{
                        root.classList.add('theme-' + saved);
                    }}
                }} catch (e) {{ /* noop */ }}
            }})();
        </script>
    </head>
    <body>
        <div class="container">
            <nav>
                <div class="nav-row">
                    <ul>
                        <li><a href="/about" class="nav-link">About</a></li>
                        <li><a href="/articles" class="nav-link">Articles</a></li>
                        <li><a href="/album" class="nav-link">Album</a></li>
                        <li><a href="/utilities" class="nav-link active">Utilities</a></li>
                    </ul>
                    <div class="theme-toggle">
                        <div id="theme-toggle" class="theme-switch" role="button" tabindex="0" aria-label="Toggle theme" title="Toggle theme">
                            <i class="fa-solid fa-sun switch-icon sun" aria-hidden="true"></i>
                            <span class="switch-thumb"></span>
                            <i class="fa-solid fa-moon switch-icon moon" aria-hidden="true"></i>
                        </div>
                    </div>
                </div>
            </nav>
            <div id="utilities" class="page active">
                <div class="utilities-intro">
                    <h1>{html_escape(headline)}</h1>
                    {'<p class="utilities-description">{}</p>'.format(html_escape(blurb)) if blurb else ''}
                </div>
                <div class="utilities-list">
{cards_block}
                </div>
            </div>
            <div class="footer">me (at) ethan (dot) dev</div>
        </div>
        <script>
            (function() {{
                const root = document.documentElement;
                const prefersLight = window.matchMedia('(prefers-color-scheme: light)');

                function currentExplicitTheme() {{
                    try {{ return localStorage.getItem('theme'); }} catch (_) {{ return null; }}
                }}

                function applyTheme(theme) {{
                    root.classList.remove('theme-light', 'theme-dark');
                    if (theme === 'light' || theme === 'dark') {{
                        root.classList.add('theme-' + theme);
                    }}
                    updateThemeToggleState();
                }}

                function updateThemeToggleState() {{
                    const sw = document.getElementById('theme-toggle');
                    if (!sw) return;
                    const isLight = root.classList.contains('theme-light') || (!root.classList.contains('theme-dark') && prefersLight.matches);
                    sw.setAttribute('aria-pressed', String(isLight));
                }}

                function toggleTheme() {{
                    const explicit = currentExplicitTheme();
                    let next;
                    if (explicit) {{
                        next = explicit === 'light' ? 'dark' : 'light';
                    }} else {{
                        next = prefersLight.matches ? 'dark' : 'light';
                    }}
                    try {{ localStorage.setItem('theme', next); }} catch (_) {{}}
                    applyTheme(next);
                }}

                window.addEventListener('DOMContentLoaded', () => {{
                    const btn = document.getElementById('theme-toggle');
                    if (btn && !btn.dataset.bound) {{
                        btn.dataset.bound = '1';
                        btn.addEventListener('click', toggleTheme);
                        btn.addEventListener('keydown', (e) => {{
                            if (e.key === 'Enter' || e.key === ' ') {{
                                e.preventDefault();
                                toggleTheme();
                            }}
                        }});
                        updateThemeToggleState();
                    }}
                }});

                try {{
                    prefersLight.addEventListener('change', () => {{
                        if (!currentExplicitTheme()) {{
                            applyTheme(null);
                        }}
                    }});
                }} catch (_) {{}}
            }})();
        </script>
    </body>
    </html>
    ''')

    output_path = utilities_dir / 'index.html'
    output_path.write_text(template.lstrip(), encoding='utf-8')
    print(f"  ✓ Created utilities/index.html")

def main():
    # Get project root (two levels up from this script)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    posts_dir = project_root / 'posts'
    
    # Process each markdown file
    for md_file in posts_dir.glob('*.md'):
        # Skip template
        if md_file.name.startswith('_'):
            continue
        
        post_id = md_file.stem
        print(f"Processing {post_id}...")
        
        # Read markdown
        content = md_file.read_text(encoding='utf-8')
        
        # Parse frontmatter
        metadata, markdown_content = parse_frontmatter(content)
        
        # Convert to HTML
        html_content = markdown_to_html(markdown_content)
        
        # Create full HTML page
        full_html = create_article_html(post_id, metadata, html_content)
        
        # Create article directory at root level (e.g., /convergence/)
        article_dir = project_root / post_id
        article_dir.mkdir(exist_ok=True)
        
        # Write to root-level directory as index.html
        output_file = article_dir / 'index.html'
        output_file.write_text(full_html, encoding='utf-8')
        print(f"  ✓ Created {output_file}")
    
    build_utilities_page(project_root)
    
    print("\nDone! All markdown files converted to HTML and utilities page generated.")

if __name__ == '__main__':
    main()
