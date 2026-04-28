const { scrape: scrapeDM } = require('./scrapers/design-milk.js');
const { scrape: scrapeGD } = require('./scrapers/good-design.js');
const { scrape: scrapeBing } = require('./scrapers/bing-search.js');

async function test() {
  console.log('=== Testing Design Milk ===');
  try {
    const dm = await scrapeDM();
    console.log('Items:', dm.items ? dm.items.length : 0);
    if (dm.items && dm.items.length > 0) {
      dm.items.slice(0, 3).forEach((item, i) => {
        console.log('  ' + (i+1) + '. ' + (item.title || '').substring(0, 60));
      });
    }
    if (dm.error) console.log('Error:', dm.error);
  } catch(e) { console.log('Failed:', e.message); }

  console.log('\n=== Testing Good Design ===');
  try {
    const gd = await scrapeGD();
    console.log(JSON.stringify(gd, null, 2).substring(0, 300));
  } catch(e) { console.log('Failed:', e.message); }

  console.log('\n=== Testing Bing Search ===');
  try {
    const bg = await scrapeBing();
    console.log(JSON.stringify(bg, null, 2).substring(0, 300));
  } catch(e) { console.log('Failed:', e.message); }
}

test();
