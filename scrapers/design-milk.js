// 🥛 Design Milk RSS Scraper
async function scrape() {
  const items = [];
  
  try {
    const resp = await fetch('https://feeds.feedburner.com/design-milk', {
      headers: { 'User-Agent': 'Mozilla/5.0' }
    });
    const xml = await resp.text();
    
    // Simple RSS parsing without external lib
    const itemRegex = /<item>([\s\S]*?)<\/item>/g;
    let match;
    while ((match = itemRegex.exec(xml)) !== null) {
      const itemXml = match[1];
      const title = itemXml.match(/<title[^>]*><!\[CDATA\[(.*?)\]\]><\/title>/)?.[1] 
                 || itemXml.match(/<title[^>]*>(.*?)<\/title>/)?.[1] 
                 || 'Untitled';
      const link = itemXml.match(/<link[^>]*>(.*?)<\/link>/)?.[1] || '';
      const desc = itemXml.match(/<description[^>]*><!\[CDATA\[(.*?)\]\]><\/description>/)?.[1]
                || itemXml.match(/<description[^>]*>(.*?)<\/description>/)?.[1]
                || '';
      const pubDate = itemXml.match(/<pubDate[^>]*>(.*?)<\/pubDate>/)?.[1] || '';
      
      items.push({
        title: title.replace(/<!\[CDATA\[|\]\]>/g, '').trim(),
        url: link,
        description: desc.replace(/<[^>]+>/g, '').substring(0, 200),
        date: pubDate,
        source: 'Design Milk'
      });
    }
  } catch(e) {
    return { source: 'Design Milk', error: e.message, items: [] };
  }
  
  return { source: 'Design Milk', items };
}

module.exports = { scrape };
