export default async function handler(req, res) {
  try {
    const id = String(req.query?.id || '').trim();
    const pages = Math.min(10, Math.max(1, Number(req.query?.pages || 3)));
    if (!id) return res.status(400).json({ error: 'App id required' });

    const target = pages * 50;
    const reviews = [];
    const seen = new Set();
    const pageStats = [];
    const text = v => String(v?.label ?? v ?? '').trim();

    function addEntries(entries, sort, page) {
      const list = Array.isArray(entries) ? entries : entries ? [entries] : [];
      let added = 0;
      for (const entry of list) {
        const rating = Number(text(entry?.['im:rating']));
        if (!rating) continue;
        const reviewId = text(entry?.id) || `${text(entry?.author?.name)}:${text(entry?.title)}:${text(entry?.content)}`;
        if (!reviewId || seen.has(reviewId)) continue;
        seen.add(reviewId);
        reviews.push({ review: text(entry?.content), rating, title: text(entry?.title), author: text(entry?.author?.name), version: text(entry?.['im:version']), source: sort, sourcePage: page });
        added++;
        if (reviews.length >= target) break;
      }
      return added;
    }

    async function fetchFeed(page, sort) {
      const url = `https://itunes.apple.com/us/rss/customerreviews/page=${page}/id=${encodeURIComponent(id)}/sortby=${sort}/json?cb=${Date.now()}-${page}`;
      const r = await fetch(url, { cache: 'no-store', headers: { Accept: 'application/json,text/plain,*/*', 'Cache-Control': 'no-cache, no-store, max-age=0', Pragma: 'no-cache', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36' } });
      if (!r.ok) return { status: r.status, entries: [] };
      const data = await r.json();
      return { status: r.status, entries: data?.feed?.entry || [] };
    }

    // Apple's undocumented feed can have empty intermediate pages. Scan the
    // whole available 10-page window instead of assuming pages 1..N are full.
    for (let p = 1; p <= 10 && reviews.length < target; p++) {
      try {
        const result = await fetchFeed(p, 'mostrecent');
        pageStats.push({ page: p, sort: 'mostRecent', status: result.status, added: addEntries(result.entries, 'mostRecent', p) });
      } catch (e) {
        pageStats.push({ page: p, sort: 'mostRecent', status: 0, added: 0, error: e.message });
      }
    }

    // If recent-order pages contain holes, fill the requested analysis sample
    // with unique reviews from Apple's helpful ordering.
    if (reviews.length < target) {
      for (let p = 1; p <= 10 && reviews.length < target; p++) {
        try {
          const result = await fetchFeed(p, 'mosthelpful');
          pageStats.push({ page: p, sort: 'mostHelpful', status: result.status, added: addEntries(result.entries, 'mostHelpful', p) });
        } catch (e) {
          pageStats.push({ page: p, sort: 'mostHelpful', status: 0, added: 0, error: e.message });
        }
      }
    }

    const output = reviews.slice(0, target);
    res.setHeader('Cache-Control', 'no-store, max-age=0');
    return res.status(200).json({ reviews: output, requestedPages: pages, requestedReviews: target, fetchedReviews: output.length, pageStats, note: output.length < target ? `Apple exposed ${output.length} unique reviews in the available US feed window.` : null });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
