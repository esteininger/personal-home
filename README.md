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
- `articles.html` - Articles page
- `styles.css` - All CSS styles
- `posts/` - Directory containing blog posts in Markdown format (source files)
- `articles/` - Directory containing generated HTML article pages
- `images/` - Directory containing image data and assets

## Adding New Blog Posts

1. Create a new `.md` file in the `posts/` directory
2. Use the filename as the post ID (e.g., `my-new-post.md`)
3. Include frontmatter at the top of the file:

```markdown
---
title: "Your Post Title"
date: "YYYY-MM-DD"
description: "Brief description of your post"
---

# Your Post Title

Your content here...
```

4. Run the conversion script to generate HTML:

```bash
python3 scripts/python/convert_markdown_to_html.py
```

5. Add the new file to the `postFiles` array in `index.html`:

```javascript
const postFiles = [
    'posts/freedom.md',
    'posts/consolidation.md',
    'posts/convergence.md',
    'posts/geopolitics.md',
    'posts/my-new-post.md'  // Add your new post here
];
```

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
- **Navigation** - Single-page app with smooth transitions
- **Dark Theme** - Clean, minimal design

## Running Locally

1. Start a local server (required for loading markdown files):
   ```bash
   python3 -m http.server 8000
   # or
   npx serve .
   ```

2. Open `http://localhost:8000` in your browser

## File Structure

```
.
├── index.html                 # Main SPA
├── articles.html              # Articles page
├── styles.css                 # CSS styles
├── articles.css               # Article-specific styles
├── posts/                     # Blog posts (markdown source)
│   ├── _template.md           # Template for new posts
│   ├── freedom.md
│   ├── consolidation.md
│   ├── convergence.md
│   └── geopolitics.md
├── articles/                  # Generated HTML articles
│   ├── freedom.html
│   ├── consolidation.html
│   ├── convergence.html
│   └── geopolitics.html
├── images/                    # Images directory
│   └── gallery.json           # Gallery images data
├── scripts/                   # Utility scripts
│   └── python/
│       ├── convert_markdown_to_html.py
│       ├── bulk_add_to_gallery.py
│       └── ...
└── README.md                  # This file
```
