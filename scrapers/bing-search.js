// 🔍 Bing Design Search Scraper - works without JS!
const https = require('https');

async function scrape() {
  const categories = [
    '创意小物 设计 水杯 台灯 收纳 厨具',
    'creative product design kitchen lighting storage',
    'industrial design award 2025 2026 tableware',
    '收纳设计 氛围灯 日历 钥匙扣 创意好物',
  ];
  
  const results = [];
  
  for (const query of categories) {
    try {
      const url = `https://www.bing.com/search?q=${encodeURIComponent(query)}`;
      const resp = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' }
      });
      const html = await resp.text();
      
      // Extract search result titles and descriptions
      const titles = html.match(/<h2><a[^>]*>(.*?)<\/a><\/h2>/g) || [];
      const snippets = html.match(/<p class="b_lineclamp[^"]*">(.*?)<\/p>/g) || [];
      
      results.push({
        query,
        status: 'ok',
        resultCount: Math.min(titles.length, 5)
      });
    } catch(e) {
      results.push({ query, status: 'error', error: e.message });
    }
  }
  
  return { source: 'Bing Search', raw: results };
}

module.exports = { scrape };
