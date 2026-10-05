export default async function handler(req, res) {
  try {
    const id = String(req.query?.id || '').trim();
    const pages = Math.min(10, Math.max(1, Number(req.query?.pages || 3)));
    if (!id) return res.status(400).json({ error: 'App id required' });

    const reviews = [];
    const seen = new Set();
    const pageStats = [];

    const text = v => String(v?.label ?? v ?? '').trim();

    for (let p = 1; p <= pages; p++) {
      // Apple's JSON RSS endpoint respects the page segment. The previous XML
      // implementation could return the same first page repeatedly, which was
      // then deduplicated down to 50 reviews regardless of the user's choice.
      const url = `https://itunes.apple.com/us/rss/customerreviews/page=${p}/id=${encodeURIComponent(id)}/sortby=mostrecent/json`;
      const r = await fetch(url, {
        cache: 'no-store',
        headers: {
          Accept: 'application/json',
          'User-Agent': 'ReviewIntelligence/1.0'
        }
      });

      if (!r.ok) {
        pageStats.push({ page: p, status: r.status, received: 0, added: 0 });
        continue;
      }

      let data;
      try {
        data = await r.json();
      } catch {
        pageStats.push({ page: p, status: r.status, received: 0, added: 0 });
        continue;
      }

      const entries = Array.isArray(data?.feed?.entry) ? data.feed.entry : [];
      let added = 0;
      let received = 0;

      for (const entry of entries) {
        const rating = Number(text(entry?.['im:rating']));
        if (!rating) continue; // Apple includes one app metadata entry on page 1.
        received++;

        const reviewId = text(entry?.id) || `${p}:${text(entry?.author?.name)}:${text(entry?.title)}:${text(entry?.updated)}`;
        if (seen.has(reviewId)) continue;
        seen.add(reviewId);

        reviews.push({
          review: text(entry?.content),
          rating,
          title: text(entry?.title),
          author: text(entry?.author?.name),
          version: text(entry?.['im:version'])
        });
        added++;
      }

      pageStats.push({ page: p, status: r.status, received, added });
    }

    res.setHeader('Cache-Control', 'no-store, max-age=0');
    return res.status(200).json({
      reviews,
      requestedPages: pages,
      fetchedReviews: reviews.length,
      pageStats
    });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
