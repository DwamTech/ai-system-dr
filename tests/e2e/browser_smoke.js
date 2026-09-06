const { chromium } = require('playwright');

const url = process.env.APP_URL || 'http://127.0.0.1:8502';
const executablePath = process.env.BROWSER_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const viewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 768, height: 900 },
  { name: 'mobile390', width: 390, height: 844 },
  { name: 'mobile375', width: 375, height: 812 },
];
const tabs = ['المحادثة', 'الملخص', 'الكيانات', 'الترجمة', 'التحليل', 'الخريطة الذهنية', 'البحث الأكاديمي'];

(async () => {
  const browser = await chromium.launch({ executablePath, headless: true });
  const evidence = [];
  try {
    for (const viewport of viewports) {
      const context = await browser.newContext({ viewport });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(`page: ${error.message}`));
      page.on('console', message => {
        if (message.type() === 'error') errors.push(`console: ${message.text()}`);
      });
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.getByRole('heading', { name: /محرك البحث الأكاديمي/ }).waitFor({ timeout: 60000 });
      const tabList = page.getByRole('tab');
      if (await tabList.count() !== 7) throw new Error(`${viewport.name}: expected seven tabs`);
      for (const label of tabs) {
        const tab = page.getByRole('tab', { name: label });
        await tab.click();
        if (await tab.getAttribute('aria-selected') !== 'true') throw new Error(`${viewport.name}: tab ${label} did not activate`);
      }
      const geometry = await page.evaluate(() => ({
        innerWidth: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
      }));
      if (geometry.scrollWidth > geometry.innerWidth + 1) throw new Error(`${viewport.name}: horizontal page overflow`);
      if ((await page.getByText('جولة تعريفية', { exact: true }).count()) > 0) throw new Error(`${viewport.name}: removed guided tour is visible`);
      if (errors.length) throw new Error(`${viewport.name}: ${errors.join(' | ')}`);
      evidence.push({ viewport: viewport.name, tabs: 7, overflow: false, page_errors: 0 });
      await context.close();
    }
    process.stdout.write(JSON.stringify({ status: 'passed', evidence }) + '\n');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
