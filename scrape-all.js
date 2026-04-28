// 🎨 Daily Design Digest - Master Scraper
// Runs all scrapers and generates the daily digest JSON

const fs = require('fs');
const path = require('path');

async function runAll() {
  console.log('🎨 Daily Design Digest Scraper');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`📅 ${new Date().toLocaleDateString('zh-CN')}\n`);
  
  const results = {};
  const failed = [];
  
  // Run scrapers
  const scrapers = [
    { name: 'design-milk', file: './scrapers/design-milk.js' },
    { name: 'good-design', file: './scrapers/good-design.js' },
    { name: 'bing-search', file: './scrapers/bing-search.js' },
  ];
  
  for (const scraper of scrapers) {
    try {
      const mod = require(scraper.file);
      const data = await mod.scrape();
      results[scraper.name] = data;
      console.log(`✅ ${scraper.name}: ${data.items ? data.items.length + ' items' : 'ok'}`);
    } catch(e) {
      failed.push(scraper.name);
      console.log(`❌ ${scraper.name}: ${e.message}`);
    }
  }
  
  // Build digest
  const digest = {
    date: new Date().toISOString().split('T')[0],
    timestamp: new Date().toISOString(),
    stats: {
      total: Object.values(results).reduce((sum, r) => sum + ((r.items || []).length || 0), 0),
      sources: Object.keys(results).length,
      failed: failed
    },
    sources: results,
    items: []
  };
  
  // Flatten items for easy use
  for (const [key, data] of Object.entries(results)) {
    if (data.items) {
      for (const item of data.items) {
        digest.items.push({ ...item, source: data.source || key });
      }
    }
  }
  
  // Write output
  const outputDir = path.join(__dirname, 'data');
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir);
  
  const filename = `digest-${digest.date}.json`;
  fs.writeFileSync(path.join(outputDir, filename), JSON.stringify(digest, null, 2));
  fs.writeFileSync(path.join(outputDir, 'latest.json'), JSON.stringify(digest, null, 2));
  
  console.log(`\n✅ Saved: ${filename}`);
  console.log(`📊 Total items: ${digest.stats.total}`);
  if (failed.length) console.log(`⚠️ Failed: ${failed.join(', ')}`);
  
  return digest;
}

if (require.main === module) {
  runAll().catch(console.error);
}

module.exports = { runAll };
