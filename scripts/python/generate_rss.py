#!/usr/bin/env python3
"""
Generate an RSS 2.0 feed (rss.xml) from markdown posts in posts/ using frontmatter.

- Reads frontmatter keys: title, date (YYYY-MM-DD), description
- Outputs rss.xml at the project root
"""

from __future__ import annotations

import re
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List


def read_domain(project_root: Path) -> str:
    cname = project_root / 'CNAME'
    try:
        content = cname.read_text(encoding='utf-8').strip()
        if content:
            # CNAME may contain multiple lines; use the first
            domain = content.splitlines()[0].strip()
            # Basic sanitation
            domain = domain.replace('http://', '').replace('https://', '').strip('/')
            return domain
    except Exception:
        pass
    return 'localhost'


def parse_frontmatter(content: str) -> (Dict[str, str], str):
    pattern = r'^---\n(.*?)\n---\n(.*)$'
    m = re.match(pattern, content, re.DOTALL)
    if not m:
        return {}, content
    fm_text, markdown = m.group(1), m.group(2)
    metadata: Dict[str, str] = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            metadata[key] = value
    return metadata, markdown


def escape_xml(text: str) -> str:
    return (
        text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
    )


def ymd_to_rfc2822(ymd: str) -> str:
    try:
        dt = datetime.strptime(ymd, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)
    # RFC 2822 (e.g., Tue, 03 Oct 2023 00:00:00 GMT)
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')


def collect_posts(posts_dir: Path) -> List[Dict[str, str]]:
    posts: List[Dict[str, str]] = []
    for md_file in sorted(posts_dir.glob('*.md')):
        if md_file.name.startswith('_'):
            continue
        content = md_file.read_text(encoding='utf-8')
        metadata, _ = parse_frontmatter(content)
        post_id = md_file.stem
        title = metadata.get('title', post_id)
        date = metadata.get('date', '')
        description = metadata.get('description', '')
        posts.append({
            'id': post_id,
            'title': title,
            'date': date,
            'description': description,
        })
    # Sort newest first by date (fall back to filename order)
    def sort_key(p: Dict[str, str]):
        try:
            return datetime.strptime(p.get('date', ''), '%Y-%m-%d')
        except Exception:
            return datetime.min
    posts.sort(key=sort_key, reverse=True)
    return posts


def build_rss_xml(domain: str, posts: List[Dict[str, str]]) -> str:
    base_url = f'https://{domain}'
    channel_title = 'ethan - articles'
    channel_link = f'{base_url}/articles'
    channel_description = 'Articles by Ethan'
    language = 'en-US'

    last_build = None
    for p in posts:
        try:
            dt = datetime.strptime(p.get('date', ''), '%Y-%m-%d')
            if (last_build is None) or (dt > last_build):
                last_build = dt
        except Exception:
            continue
    last_build_rfc = (last_build.replace(tzinfo=timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT') if last_build else datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'))

    items_xml: List[str] = []
    for p in posts:
        title = escape_xml(p['title'])
        # Prefer stable static HTML page for permalink
        link = f'{base_url}/articles/{p["id"]}.html'
        guid = link
        pub_date = ymd_to_rfc2822(p.get('date', ''))
        description = p.get('description', '')
        if description:
            desc_xml = f'<![CDATA[{description}]]>'
        else:
            desc_xml = ''
        items_xml.append(
            '\n'.join([
                '    <item>',
                f'      <title>{title}</title>',
                f'      <link>{link}</link>',
                f'      <guid isPermaLink="true">{guid}</guid>',
                f'      <pubDate>{pub_date}</pubDate>',
                f'      <description>{desc_xml}</description>',
                '    </item>'
            ])
        )

    xml = '\n'.join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        '  <channel>',
        f'    <title>{escape_xml(channel_title)}</title>',
        f'    <link>{channel_link}</link>',
        f'    <description>{escape_xml(channel_description)}</description>',
        f'    <language>{language}</language>',
        f'    <lastBuildDate>{last_build_rfc}</lastBuildDate>',
        *items_xml,
        '  </channel>',
        '</rss>',
        ''
    ])
    return xml


def main() -> None:
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent
    posts_dir = project_root / 'posts'
    output_file = project_root / 'rss.xml'

    domain = read_domain(project_root)
    posts = collect_posts(posts_dir)
    rss_xml = build_rss_xml(domain, posts)
    output_file.write_text(rss_xml, encoding='utf-8')
    print(f'Wrote RSS with {len(posts)} items to {output_file}')


if __name__ == '__main__':
    main()



