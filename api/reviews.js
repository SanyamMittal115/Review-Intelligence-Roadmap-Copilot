export default async function handler(req, res) {
  try {
    const id = String(req.query?.id || '').trim();
    const requestedPages = Math.min(10, Math.max(1, Number(req.query?.pages || 3)));
    if (!id) return res.status(400).json({ error: 'App id required' });

    const target = requestedPages * 50;
    const reviews = [];
    const seen = new Set();
    const pageStats = [];
    const text = v => String(v?.label ?? v ?? '').trim();

    function reviewKey(entry) {
      const idValue = text(entry?.id);
      if (idValue) return `id:${idValue}`;
      return `body:${text(entry?.author?.name)}|${text(entry?.title)}|${text(entry?.content)}|${text(entry?.['im:rating'])}`;
    }

    function addEntries(entries, sort, page) {
      const list = Array.isArray(entries) ? entries : entries ? [entries] : [];
      let added = 0;
      for (const entry of list) {
        if (reviews.length >= target) break;
        const rating = Number(text(entry?.['im:rating']));
        const body = text(entry?.content);
        if (!rating || !body) continue;
        const key = reviewKey(entry);
        if (seen.has(key)) continue;
        seen.add(key);
        reviews.push({
          review: body,
          rating,
          title: text(entry?.title),
          author: text(entry?.author?.name),
          version: text(entry?.['im:version']),
          source: sort,
          sourcePage: page
        });
        added++;
      }
      return added;
    }

    async function fetchFeed(page, sort) {
      const sortToken = sort === 'mostHelpful' ? 'mosthelpful' : 'mostrecent';
      const url = `https://itunes.apple.com/us/rss/customerreviews/page=${page}/id=${encodeURIComponent(id)}/sortby=${sortToken}/json?cb=${Date.now()}-${sortToken}-${page}`;
      const r = await fetch(url, {
        cache: 'no-store',
        headers: {
          Accept: 'application/json,text/plain,*/*',
          'Cache-Control': 'no-cache, no-store, max-age=0',
          Pragma: 'no-cache',
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36'
        }
      });
      if (!r.ok) return { status: r.status, entries: [] };
      const data = await r.json();
      return { status: r.status, entries: data?.feed?.entry || [] };
    }

    // Exact-count strategy: the user's selection is a target review count,
    // not a promise that the first N Apple pages are complete. Scan every
    // public feed page and both supported orderings until target unique reviews
    // are collected or Apple's public feed is exhausted.
    for (const sort of ['mostRecent', 'mostHelpful']) {
      for (let page = 1; page <= 10 && reviews.length < target; page++) {
        try {
          const result = await fetchFeed(page, sort);
          const added = addEntries(result.entries, sort, page);
          pageStats.push({ page, sort, status: result.status, returned: Array.isArray(result.entries) ? result.entries.length : 0, added });
        } catch (e) {
          pageStats.push({ page, sort, status: 0, returned: 0, added: 0, error: e.message });
        }
      }
    }

    const output = reviews.slice(0, target);
    const exact = output.length === target;
    res.setHeader('Cache-Control', 'no-store, max-age=0');
    return res.status(200).json({
      reviews: output,
      requestedPages,
      requestedReviews: target,
      fetchedReviews: output.length,
      exact,
      availableReviews: output.length,
      pageStats,
      note: exact ? null : `Requested ${target} unique reviews, but Apple's public feed exposed only ${output.length} unique written reviews for this app.`
    });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
