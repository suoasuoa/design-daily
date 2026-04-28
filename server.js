// 🎨 Daily Design Digest Server
// Auto-scrapes design inspiration sources and generates daily reports

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3456;
const DATA_FILE = path.join(__dirname, 'daily-data.json');

// ====== DATA SOURCES ======
// We'll scrape what we can and serve a beautiful page

// 1. GOOD DESIGN AWARD - Try to get recent winners
async function scrapeGoodDesign() {
  try {
    const response = await fetch('https://www.g-mark.org/', {
      headers: { 'User-Agent': 'Mozilla/5.0' }
    });
    const html = await response.text();
    
    // Extract from __NEXT_DATA__
    const match = html.match(/<script id="__NEXT_DATA__" type="application\/json">(.*?)<\/script>/s);
    if (match) {
      const data = JSON.parse(match[1]);
      return { source: 'g-mark', status: 'scraped', data: data };
    }
    return { source: 'g-mark', status: 'no-data' };
  } catch (e) {
    return { source: 'g-mark', status: 'error', error: e.message };
  }
}

// 2. DESIGN MILK RSS - Working!
async function scrapeDesignMilk() {
  try {
    const parser = new (require('feedparser'))();
    // Use simple fetch
    const response = await fetch('https://feeds.feedburner.com/design-milk', {
      headers: { 'User-Agent': 'Mozilla/5.0' }
    });
    const text = await response.text();
    return { source: 'design-milk', status: 'scraped', content: text.substring(0, 500) };
  } catch (e) {
    return { source: 'design-milk', status: 'error', error: e.message };
  }
}

// 3. XIAOHONGSHU - Will need playwrite/node
async function scrapeXiaohongshu() {
  return { source: 'xiaohongshu', status: 'needs-playwright' };
}

// 4. DOUYIN - Will need playwrite/node
async function scrapeDouyin() {
  return { source: 'douyin', status: 'needs-playwright' };
}

// 5. INSTAGRAM - Will need Meta API
async function scrapeInstagram() {
  return { source: 'instagram', status: 'needs-api' };
}

// ====== MAIN ======
async function buildDailyDigest() {
  console.log('🔄 Building daily digest...');
  const results = await Promise.allSettled([
    scrapeGoodDesign(),
    scrapeDesignMilk(),
    scrapeXiaohongshu(),
    scrapeDouyin(),
    scrapeInstagram()
  ]);
  
  const digest = {
    date: new Date().toISOString(),
    sources: results.map(r => r.status === 'fulfilled' ? r.value : { status: 'failed' }),
    timestamp: Date.now()
  };
  
  fs.writeFileSync(DATA_FILE, JSON.stringify(digest, null, 2));
  console.log('✅ Digest saved');
  return digest;
}

// ====== HTTP SERVER ======
const server = http.createServer((req, res) => {
  if (req.url === '/api/digest') {
    // Return JSON data
    try {
      const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));
      res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
      res.end(JSON.stringify(data));
    } catch {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'no-data-yet' }));
    }
  } 
  else if (req.url === '/api/refresh') {
    // Trigger a refresh
    buildDailyDigest().then(() => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok' }));
    }).catch(e => {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'error', error: e.message }));
    });
  }
  else if (req.url === '/' || req.url === '/index.html') {
    // Serve the main HTML page
    const htmlPath = path.join(__dirname, 'index.html');
    if (fs.existsSync(htmlPath)) {
      const html = fs.readFileSync(htmlPath, 'utf-8');
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
    } else {
      res.writeHead(404);
      res.end('Not found');
    }
  }
  else {
    res.writeHead(404);
    res.end('Not found');
  }
});

server.listen(PORT, () => {
  console.log(`
🎨 Daily Design Digest Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 http://localhost:${PORT}
📂 Dashboard: http://localhost:${PORT}/
🔄 API:       http://localhost:${PORT}/api/digest
🔁 Refresh:   http://localhost:${PORT}/api/refresh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`);
});
