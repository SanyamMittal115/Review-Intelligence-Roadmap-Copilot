export default async function handler(req, res) {
  try {
    const id = String(req.query?.id || '').trim();
    const pages = Math.min(10, Math.max(1, Number(req.query?.pages || 3)));
    if (!id) return res.status(400).json({ error: 'App id required' });

    const reviews = [];
    const seen = new Set();
    const pageStats = [];

    for (let p = 1; p <= pages; p++) {
      // Apple's public customer-review feed is storefront + page specific.
      // Request XML explicitly because the legacy /json route can return an
      // empty/non-review payload on Vercel even when reviews exist.
      const url = `https://itunes.apple.com/us/rss/customerreviews/page=${p}/id=${encodeURIComponent(id)}/sortby=mostrecent/xml`;
      const r = await fetch(url, {
        headers: {
          'Accept': 'application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8',
          'User-Agent': 'Mozilla/5.0 ReviewIntelligence/1.0'
        }
      });

      if (!r.ok) {
        pageStats.push({ page: p, status: r.status, count: 0 });
        continue;
      }

      const xml = await r.text();
      const entries = [...xml.matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map(m => m[1]);
      let added = 0;

      const decode = (s = '') => s
        .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;|&apos;/g, "'")
        .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
        .trim();
      const get = (entry, tag) => {
        const escaped = tag.replace(':', '\\:');
        const m = entry.match(new RegExp(`<${escaped}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${escaped}>`));
        return m ? decode(m[1]) : '';
      };

      for (const entry of entries) {
        const rating = Number(get(entry, 'im:rating'));
        if (!rating) continue; // skips the app metadata entry
        const reviewId = get(entry, 'id') || `${p}:${get(entry, 'author')}:${get(entry, 'title')}:${get(entry, 'updated')}`;
        if (seen.has(reviewId)) continue;
        seen.add(reviewId);
        reviews.push({
          review: get(entry, 'content'),
          rating,
          title: get(entry, 'title'),
          author: get(entry, 'name'),
          version: get(entry, 'im:version')
        });
        added++;
      }
      pageStats.push({ page: p, status: r.status, count: added });
    }

    return res.status(200).json({ reviews, requestedPages: pages, fetchedReviews: reviews.length, pageStats });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
