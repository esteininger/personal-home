# SEO/GEO Optimization Guide

This guide documents the SEO best practices for all pages on ethan.dev. Follow this checklist whenever creating a new page to ensure optimal search engine and social media discovery.

---

## Required Meta Tags (All Pages)

Every HTML page must include these basic meta tags in the `<head>` section:

```html
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Page Title - ethan.dev</title>
<meta name="description" content="Clear, concise description of the page (150-160 characters)">
```

---

## Open Graph Tags (Social Media Previews)

Add these for proper Facebook, LinkedIn, and other social media previews:

```html
<meta property="og:title" content="Page Title">
<meta property="og:description" content="Page description matching the meta description">
<meta property="og:type" content="website"> <!-- or "article" for blog posts -->
<meta property="og:url" content="https://ethan.dev/page-slug">
```

**For article pages, add:**
```html
<meta property="article:published_time" content="2025-01-21">
<meta property="article:author" content="Ethan Steininger">
```

---

## Twitter Card Tags

Add these for optimized Twitter previews:

```html
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="Page Title">
<meta name="twitter:description" content="Page description matching the meta description">
```

---

## Canonical URL

Always include a canonical URL to prevent duplicate content issues:

```html
<link rel="canonical" href="https://ethan.dev/page-slug">
```

---

## Structured Data (JSON-LD)

Add structured data before the closing `</head>` tag. Choose the appropriate schema type:

### Person Schema (About/Home Page)

```html
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Person",
    "name": "Ethan Steininger",
    "url": "https://ethan.dev",
    "image": "https://ethan.dev/images/ethan.jpeg",
    "sameAs": [
        "https://github.com/esteininger",
        "https://www.linkedin.com/in/ethansteininger/",
        "https://x.com/ethansteininger"
    ],
    "jobTitle": "Founder",
    "worksFor": {
        "@type": "Organization",
        "name": "Mixpeek",
        "url": "https://mixpeek.com"
    },
    "description": "Building Mixpeek — infrastructure for making video, image, audio, and text searchable."
}
</script>
```

### Article Schema (Blog Posts)

```html
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "Article Title",
    "description": "Article description",
    "datePublished": "2025-01-21",
    "author": {
        "@type": "Person",
        "name": "Ethan Steininger",
        "url": "https://ethan.dev"
    },
    "publisher": {
        "@type": "Person",
        "name": "Ethan Steininger"
    },
    "url": "https://ethan.dev/article-slug"
}
</script>
```

### Blog Schema (Articles Index Page)

```html
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Blog",
    "name": "Ethan Steininger's Articles",
    "description": "Long-form essays and analysis on software engineering, geopolitics, AI, and technology.",
    "url": "https://ethan.dev/articles",
    "author": {
        "@type": "Person",
        "name": "Ethan Steininger",
        "url": "https://ethan.dev"
    },
    "publisher": {
        "@type": "Person",
        "name": "Ethan Steininger"
    }
}
</script>
```

### SoftwareApplication Schema (Utility Tools)

```html
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "Tool Name",
    "description": "Tool description",
    "applicationCategory": "CategoryName",
    "operatingSystem": "Any modern browser",
    "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD"
    },
    "url": "https://ethan.dev/utilities/tool-slug"
}
</script>
```

---

## Complete Examples

### Example 1: New Article Page

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ethan - article-title</title>
    <meta name="description" content="Brief description of the article content (150-160 chars).">
    <meta property="og:title" content="article-title - Ethan Steininger">
    <meta property="og:description" content="Brief description of the article content.">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://ethan.dev/article-slug">
    <meta property="article:published_time" content="2025-01-21">
    <meta property="article:author" content="Ethan Steininger">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="article-title - Ethan Steininger">
    <meta name="twitter:description" content="Brief description of the article content.">
    <link rel="canonical" href="https://ethan.dev/article-slug">

    <!-- Stylesheets and fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/styles.css">
    <link rel="stylesheet" href="/articles.css">
    <link rel="icon" href="/images/favicon.ico" type="image/x-icon">

    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Article Title",
        "description": "Brief description of the article content.",
        "datePublished": "2025-01-21",
        "author": {
            "@type": "Person",
            "name": "Ethan Steininger",
            "url": "https://ethan.dev"
        },
        "publisher": {
            "@type": "Person",
            "name": "Ethan Steininger"
        },
        "url": "https://ethan.dev/article-slug"
    }
    </script>
</head>
<body>
    <!-- Page content -->
</body>
</html>
```

### Example 2: New Utility Tool Page

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tool Name - ethan.dev</title>
    <meta name="description" content="What the tool does and its key features (150-160 chars).">
    <meta property="og:title" content="Tool Name - ethan.dev">
    <meta property="og:description" content="What the tool does and its key features.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://ethan.dev/utilities/tool-slug">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="Tool Name - ethan.dev">
    <meta name="twitter:description" content="What the tool does and its key features.">
    <link rel="canonical" href="https://ethan.dev/utilities/tool-slug">

    <!-- Stylesheets and fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../../styles.css">
    <link rel="stylesheet" href="../../utilities.css">
    <link rel="icon" href="/images/favicon.ico" type="image/x-icon">

    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "Tool Name",
        "description": "What the tool does and its key features in more detail.",
        "applicationCategory": "ToolCategory",
        "operatingSystem": "Any modern browser",
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
        },
        "url": "https://ethan.dev/utilities/tool-slug"
    }
    </script>
</head>
<body>
    <!-- Page content -->
</body>
</html>
```

---

## SEO Checklist for New Pages

Before publishing a new page, verify:

- [ ] Page title is descriptive and includes context (e.g., "Tool Name - ethan.dev")
- [ ] Meta description is 150-160 characters, compelling, and accurate
- [ ] All Open Graph tags are present (title, description, type, url)
- [ ] All Twitter Card tags are present (card, title, description)
- [ ] Canonical URL is set correctly
- [ ] Appropriate structured data (JSON-LD) is included
- [ ] For articles: publication date and author are specified
- [ ] Favicon link is present
- [ ] Page validates without errors

---

## Tips for Writing Good Descriptions

1. **Be specific**: Describe what the page actually contains
2. **Include keywords**: Use relevant terms people might search for
3. **Call to action**: Encourage clicks ("Learn how...", "Discover...", "Convert...")
4. **Stay concise**: 150-160 characters is ideal for search result snippets
5. **Match the content**: Don't mislead - describe what's actually on the page

---

## Dynamic Pages (SPA)

For Single Page Applications (like index.html), update meta tags dynamically:

```javascript
function updatePageMeta(titleText, options) {
    const opts = options || {};
    try {
        if (typeof titleText === 'string' && titleText.trim()) {
            document.title = titleText;
            upsertMeta('property', 'og:title', titleText);
            upsertMeta('name', 'twitter:title', titleText);
        }
        const description = typeof opts.description === 'string' ? opts.description.trim() : '';
        if (description) {
            upsertMeta('name', 'description', description);
            upsertMeta('property', 'og:description', description);
            upsertMeta('name', 'twitter:description', description);
        }
        if (typeof opts.canonical === 'string' && opts.canonical.trim()) {
            upsertLink('canonical', opts.canonical.trim());
            upsertMeta('property', 'og:url', opts.canonical.trim());
        }
    } catch (_) { /* noop */ }
}
```

---

## Resources

- [Google Search Central - SEO Starter Guide](https://developers.google.com/search/docs/beginner/seo-starter-guide)
- [Open Graph Protocol](https://ogp.me/)
- [Twitter Card Documentation](https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards)
- [Schema.org Documentation](https://schema.org/)
- [Google Structured Data Testing Tool](https://search.google.com/test/rich-results)

---

## Testing Your SEO

After creating a new page, test it with:

1. **Google Rich Results Test**: https://search.google.com/test/rich-results
2. **Facebook Sharing Debugger**: https://developers.facebook.com/tools/debug/
3. **Twitter Card Validator**: https://cards-dev.twitter.com/validator
4. **Lighthouse (Chrome DevTools)**: Check SEO score and recommendations

---

_Last updated: January 2026_
