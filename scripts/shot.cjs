// usage: node shot.cjs <port> <outprefix>
const { chromium } = require(process.env.NODE_PATH_PW); const [port, out] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch(); const errs = [];
  for (const [name, vp, scheme] of [['desk-light', { width: 1280, height: 900 }, 'light'], ['phone-dark', { width: 400, height: 860 }, 'dark']]) {
    const p = await b.newPage({ viewport: vp, colorScheme: scheme, reducedMotion: 'reduce' });
    p.on('console', m => { if (m.type() === 'error') errs.push(name + ': ' + m.text()); });
    p.on('pageerror', e => errs.push(name + ' pageerror: ' + e.message));
    await p.goto(`http://localhost:${port}/_test.html`, { waitUntil: 'networkidle' });
    for (let y = 0; y < 60000; y += 700) { await p.evaluate(v => window.scrollTo(0, v), y); await p.waitForTimeout(40); }
    await p.waitForTimeout(1500);
    const r = await p.evaluate(() => ({ ov: document.documentElement.scrollWidth - window.innerWidth, broken: [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src), mjx: document.querySelectorAll('mjx-container').length, mjxErr: document.querySelectorAll('mjx-merror, [data-mjx-error]').length, scope: document.querySelector('#scope').innerText.slice(0, 50) }));
    console.log(name, JSON.stringify(r));
    for (const id of ['info', 'method', 'results', 'evidence', 'chat']) { await p.evaluate(i => document.getElementById(i).scrollIntoView(), id); await p.waitForTimeout(200); await p.screenshot({ path: `${out}-${name}-${id}.png` }); }
  }
  console.log('errors', JSON.stringify(errs)); await b.close();
})();
