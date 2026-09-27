// Full-page screenshots of the preview with the system Chromium.
// Reuses the run-famille-busson skill's Playwright install (its bundled browser isn't downloaded here).
// Usage: node shoot.cjs '<json array of {url, path, width, height, mobile?, colorScheme?}>'
const { chromium } = require('/workspace/famille-busson/.claude/skills/run-famille-busson/node_modules/playwright');

(async () => {
  const shots = JSON.parse(process.argv[2]);
  const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', args: ['--no-sandbox'] });
  for (const s of shots) {
    const context = await browser.newContext({
      viewport: { width: s.width, height: s.height },
      isMobile: !!s.mobile,
      hasTouch: !!s.mobile,
      deviceScaleFactor: 1,
      colorScheme: s.colorScheme || 'light',
    });
    const page = await context.newPage();
    const problems = [];
    page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') problems.push(`${m.type()}: ${m.text()}`); });
    page.on('pageerror', (e) => problems.push(`pageerror: ${e}`));
    page.on('requestfailed', (r) => problems.push(`requestfailed: ${r.url()}`));
    await page.goto(s.url, { waitUntil: 'networkidle' });
    // Full-page captures never scroll, so lazy images below the fold would stay blank: load them all.
    await page.evaluate(async () => {
      const imgs = [...document.images];
      imgs.forEach((img) => { img.loading = 'eager'; });
      await Promise.all(imgs.map((img) => (img.complete ? null : new Promise((r) => { img.onload = img.onerror = r; }))));
    });
    await page.evaluate(() => document.fonts.ready);
    const fonts = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family));
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    const brokenImages = await page.evaluate(() => [...document.images].filter((i) => !i.naturalWidth).map((i) => i.getAttribute('src')));
    const images = await page.evaluate(() => document.images.length);
    await page.waitForTimeout(300);
    if (s.selector) {
      await page.locator(s.selector).nth(s.nth || 0).screenshot({ path: s.path });
    } else {
      await page.screenshot({ path: s.path, fullPage: true });
    }
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    console.log(JSON.stringify({ shot: s.path, height, horizontalOverflow: overflow, fonts: [...new Set(fonts)], images, brokenImages, problems }));
    await context.close();
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
