Title: I built a personal photo album with semantic search, clustering, and reverse image lookup

I travel a lot (van life, road trips through western Canada and the US) and had ~300 photos sitting in S3 with no good way to browse them beyond scrolling.

So I built an album page on my personal site (ethan.dev/album) that does three things I actually wanted:

1. **Semantic search.** Type "sunset over lake" and it finds the right photos. Not filename matching or tags I manually added. The photos are embedded with SigLIP (via Mixpeek's extraction pipeline) and searched against with a text query. Works surprisingly well for natural language descriptions of scenes.

2. **Reverse image search.** Click "find similar" on any photo and it returns the visually closest matches from the collection. Useful for finding that other angle of the same mountain you shot 20 minutes later.

3. **Visual clustering.** A t-SNE scatter plot where each dot is a thumbnail with a color-coded border showing its cluster assignment. The clusters are computed server-side (k-means on the SigLIP vectors, 20 clusters) and labeled by an LLM that looks at the nearest members. So you get labels like "Alpine Lake and Forest" or "Desert Landscape Photography" without ever tagging anything.

The whole thing is a single HTML file on GitHub Pages. No framework, no build step. The map uses Leaflet, animations use motion.js, and the cluster viz is a canvas element that progressively loads thumbnails (downsampled to tiny canvases on load so memory stays reasonable on mobile).

The Mixpeek integration is the interesting part technically. Photos go into an S3 bucket, a batch job runs SigLIP embedding extraction on a Ray cluster, the vectors land in a collection, and then everything (search, clustering, similarity) runs against that collection via API. The whole pipeline from "drop photos in S3" to "searchable and clustered" takes a few minutes for a batch of 50 images.

I'm the founder of Mixpeek so obviously I'm eating my own dog food here. But I genuinely use this page to find photos I want to share with people, and the "find similar" button is the feature I reach for most. It's weirdly satisfying to click on a photo of a trail and instantly see every other trail photo you've taken.

Some things I learned building this:

- SigLIP embeddings are remarkably good at visual similarity. Two photos of the same lake from different days end up right next to each other in the t-SNE plot.
- Canvas rendering beats DOM for scatter plots with 200+ points. The old version had a div per dot and it stuttered on mobile.
- Progressive image loading with a concurrency cap (6 on desktop, 3 on mobile) is the difference between "the page froze" and "it just works."
- k-means with 20 clusters on 500 photos gives reasonable groupings. Too few and you get "landscape" as a category. Too many and you split one hike into three clusters.

The site is live at https://ethan.dev/album if you want to poke around. Everything is static/client-side except the Mixpeek API calls.

Happy to answer questions about the embedding pipeline, the clustering approach, or anything else.
