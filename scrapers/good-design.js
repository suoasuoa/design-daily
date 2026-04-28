// 🏆 Good Design Award Scraper
// Uses Google cache + direct scraping
const https = require('https');

async function fetchWithRetry(url, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);
      const resp = await fetch(url, { 
        signal: controller.signal,
        headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' }
      });
      clearTimeout(timeout);
      if (resp.ok) return await resp.text();
    } catch(e) {}
  }
  return null;
}

async function scrape() {
  const results = [];
  
  // Try multiple approaches
  const urls = [
    'https://www.g-mark.org/search?keyword=kitchen&page=1&perPage=10',
    'https://www.g-mark.org/search?keyword=tableware&page=1&perPage=10',
    'https://www.g-mark.org/search?keyword=living&page=1&perPage=10',
    'https://www.g-mark.org/search?keyword=storage&page=1&perPage=10',
  ];
  
  for (const url of urls) {
    const html = await fetchWithRetry(url);
    if (html) {
      // Extract from meta tags and text
      const titles = html.match(/<meta[^>]*name="description"[^>]*content="([^"]*)"/g) || [];
      results.push({ url, status: 'fetched', size: html.length });
    } else {
      results.push({ url, status: 'failed' });
    }
  }
  
  return { 
    source: 'Good Design Award',
    items: [],
    note: 'G-Mark uses JS rendering. Static HTML limits available data.',
    raw: results
  };
}

module.exports = { scrape };
