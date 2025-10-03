#!/usr/bin/env python3
"""
Convert markdown posts to standalone HTML article pages.
Reads markdown files from posts/ and generates HTML files in articles/
"""

import os
import re
from pathlib import Path

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
    
    # Format date
    from datetime import datetime
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%B %d, %Y')
    except:
        formatted_date = date
    
    template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ethan - {post_id}</title>
    <meta name="twitter:card" content="summary">
    <meta property="og:type" content="website">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/styles.css">
    <link rel="stylesheet" href="/articles.css">
</head>
<body>
    <div class="container">
        <nav>
            <div class="nav-row">
                <ul>
                    <li><a href="/about" class="nav-link">About</a></li>
                    <li><a href="/articles" class="nav-link active">Articles</a></li>
                    <li><a href="/album" class="nav-link">Album</a></li>
                </ul>
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
</body>
</html>
'''
    return template

def main():
    # Get project root (two levels up from this script)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    posts_dir = project_root / 'posts'
    articles_dir = project_root / 'articles'
    
    # Create articles directory if it doesn't exist
    articles_dir.mkdir(exist_ok=True)
    
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
        
        # Write to articles directory
        output_file = articles_dir / f'{post_id}.html'
        output_file.write_text(full_html, encoding='utf-8')
        print(f"  ✓ Created {output_file}")
    
    print("\nDone! All markdown files converted to HTML.")

if __name__ == '__main__':
    main()

