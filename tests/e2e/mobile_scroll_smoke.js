const { chromium } = require('playwright');

const url = process.env.APP_URL || 'http://127.0.0.1:8502';
const executablePath = process.env.BROWSER_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const viewport = {
  width: Number(process.env.MOBILE_WIDTH || 390),
  height: Number(process.env.MOBILE_HEIGHT || 844),
};

async function scrollState(page) {
  return page.evaluate(() => {
    const candidates = [
      document.scrollingElement,
      document.querySelector('[data-testid="stAppViewContainer"]'),
      document.querySelector('[data-testid="stMain"]'),
      document.querySelector('.stApp'),
    ].filter(Boolean);
    const elements = candidates.map((element) => {
      const style = getComputedStyle(element);
      return {
        name: element === document.scrollingElement ? 'document' : element.getAttribute('data-testid') || element.className,
        top: element.scrollTop,
        height: element.clientHeight,
        scrollHeight: element.scrollHeight,
        overflowY: style.overflowY,
        touchAction: style.touchAction,
      };
    });
    return {
      elements,
      points: [100, 300, 500, 700].map(y => {
        const element = document.elementFromPoint(80, y);
        return { y, tag: element?.tagName, testid: element?.getAttribute('data-testid'), className: element?.className };
      }),
    };
  });
}

(async () => {
  const browser = await chromium.launch({ executablePath, headless: true });
  try {
    const context = await browser.newContext({
      viewport,
      isMobile: true,
      hasTouch: true,
      deviceScaleFactor: 2,
    });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.getByRole('heading', { name: /محرك البحث الأكاديمي/ }).waitFor({ timeout: 60000 });
    await page.waitForTimeout(1000);

    const before = await scrollState(page);
    await page.evaluate(() => {
      window.__scrollProbe = [];
      document.addEventListener('wheel', event => window.__scrollProbe.push({
        type: 'wheel', deltaY: event.deltaY, defaultPrevented: event.defaultPrevented,
        target: event.target?.tagName,
      }), { capture: true, passive: true });
      document.querySelector('[data-testid="stMain"]').addEventListener('scroll', event => {
        window.__scrollProbe.push({ type: 'scroll', top: event.currentTarget.scrollTop });
      }, { passive: true });
    });
    const client = await context.newCDPSession(page);
    await client.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 });
    const point = y => ({ x: 80, y, radiusX: 4, radiusY: 4, force: 1, id: 1 });
    await client.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [point(500)] });
    for (let y = 460; y >= 140; y -= 40) {
      await client.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [point(y)] });
      await page.waitForTimeout(35);
    }
    await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await page.waitForTimeout(600);
    const afterTouch = await scrollState(page);
    await page.evaluate(() => { document.querySelector('[data-testid="stMain"]').scrollTop = 0; });
    await page.waitForTimeout(100);
    await page.mouse.move(80, 500);
    await page.mouse.wheel(0, 420);
    await page.waitForTimeout(600);
    const afterWheel = await scrollState(page);
    const events = await page.evaluate(() => window.__scrollProbe);

    const touchMoved = afterTouch.elements.some((item, index) => item.top > (before.elements[index]?.top || 0) + 20);
    const wheelMoved = afterWheel.elements.some((item, index) => item.top > (before.elements[index]?.top || 0) + 20);
    const scrollable = before.elements.some(item => item.scrollHeight > item.height + 20);
    if (scrollable && (!touchMoved || !wheelMoved)) {
      throw new Error(`mobile scrolling failed: ${JSON.stringify({ touchMoved, wheelMoved, before, afterTouch, afterWheel })}`);
    }
    if (errors.length) throw new Error(`page errors: ${errors.join(' | ')}`);
    process.stdout.write(JSON.stringify({ status: 'passed', viewport, touchMoved, wheelMoved, events, before, afterTouch, afterWheel }) + '\n');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
