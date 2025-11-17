## Bulk add gallery images

Drop images into `album_inbox/` (create it at repo root if it doesn't exist), then run:

```bash
python scripts/python/bulk_add_to_gallery.py
```

Options:

```bash
python scripts/python/bulk_add_to_gallery.py \
  --dir /abs/path/to/folder \
  --bucket ethan.dev \
  --cf-domain diyjmz7hrjx3w.cloudfront.net \
  --prefix album/ \
  --name-empty \
  --no-move
```

Successful files are moved to `<dir>/processed` by default.

# Personal Website

A minimal personal website with blog functionality built with HTML, CSS, and JavaScript.

## Structure

- `index.html` - Main SPA (single page application)
- `styles.css` - All CSS styles
- `posts/` - Directory containing blog posts in Markdown format (source files)
- `/{article-name}/` - Root-level directories for each article (e.g., `/convergence/`, `/freedom/`)
- `images/` - Directory containing image data and assets

## Adding New Blog Posts

1. Create a new `.md` file in the `posts/` directory
   - Use the filename as the post ID (e.g., `my-new-post.md`)
   - You can use `posts/_template.md` as a starting template

2. Include frontmatter at the top of the file:

```markdown
---
title: "Your Post Title"
date: "YYYY-MM-DD"
description: "Brief description of your post"
---

# Your Post Title

Your content here...
```

3. Add the new file to `posts.json`:
   - Open `posts.json`
   - Add your new post path to the `posts` array (order matters - newest posts should be first)
   
```json
{
  "posts": [
    "posts/my-new-post.md",
    "posts/freedom.md",
    "posts/consolidation.md",
    "posts/convergence.md",
    "posts/geopolitics.md",
    "posts/colonialism.md"
  ]
}
```

4. Run the conversion script to generate HTML:

```bash
python3 scripts/python/convert_markdown_to_html.py
```

   This will:
   - Generate the HTML page at `/{article-name}/index.html`
   - The article will automatically appear in the blog list on your site

5. Commit and push - the site will update automatically on GitHub Pages

## Adding New Gallery Images

1. Edit `images/gallery.json` to add new image entries:

```json
{
  "url": "path/to/your/image.jpg",
  "name": "Location Name",
  "lat": 37.7749,
  "lng": -122.4194
}
```

2. The gallery will automatically update when you refresh the page.

## Features

- **Responsive Design** - Works on desktop and mobile
- **Blog Posts** - Markdown files with frontmatter metadata
- **Gallery** - Photo gallery with lightbox functionality
- **Utilities** - Client-side tools that run entirely in the browser (e.g., video converter)
- **Navigation** - Single-page app with smooth transitions
- **Dark Theme** - Clean, minimal design with light/dark mode toggle

## Running Locally

1. Start a local server (required for SPA routing and loading markdown files):
   ```bash
   python3 server.py
   ```
   This will:
   - Run the build script automatically
   - Start a server at `http://127.0.0.1:8100` (or custom HOST/PORT env vars)
   - Handle SPA routing correctly (serves `index.html` for routes like `/articles`, `/album`, etc.)

   Alternative (basic server, no SPA routing):
   ```bash
   python3 -m http.server 8000
   # or
   npx serve .
   ```

2. Open `http://localhost:8100` (or your configured port) in your browser

## File Structure

```
.
├── index.html                 # Main SPA
├── styles.css                 # CSS styles
├── articles.css               # Article-specific styles
├── utilities.css              # Shared utility styles
├── posts.json                 # List of blog posts (in order)
├── server.py                  # Local dev server with SPA routing
├── posts/                     # Blog posts (markdown source)
│   ├── _template.md           # Template for new posts
│   ├── freedom.md
│   ├── consolidation.md
│   ├── convergence.md
│   ├── geopolitics.md
│   ├── colonialism.md
│   └── guardrails.md
├── convergence/               # Generated article pages
│   └── index.html
├── freedom/
│   └── index.html
├── consolidation/
│   └── index.html
├── geopolitics/
│   └── index.html
├── colonialism/
│   └── index.html
├── utilities/                 # Client-side utility tools
│   ├── index.html             # Utilities landing page
│   └── video-converter/       # Video converter utility
│       └── index.html
├── images/                    # Images directory
│   └── gallery.json           # Gallery images data
├── scripts/                   # Utility scripts
│   └── python/
│       ├── convert_markdown_to_html.py
│       ├── bulk_add_to_gallery.py
│       └── ...
└── README.md                  # This file
```
