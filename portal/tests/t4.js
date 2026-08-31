const { chromium } = require('playwright');
const URL = 'http://localhost:8731/';
const DIR = '/tmp/claude-0/-home-user-project-office/42be28a2-4cce-5344-a3ec-34dd2a773f53/scratchpad';

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const errors = [];
  const step = async (name, fn) => {
    const before = errors.length;
    try { await fn(); } catch (e) { errors.push('STEP ' + name + ': ' + e.message); }
    console.log((errors.length > before ? 'FAIL ' : ' ok  ') + name);
  };
  const enter = async (page) => {
    await page.locator('.login-form select').selectOption({ index: 1 });
    await page.waitForTimeout(250);
    await page.locator('.login-form input[type=password]').fill('Tekstil2026');
    await page.locator('.login-form button[type=submit]').click();
    await page.waitForTimeout(1600);
  };

  // Тёмная тема
  let ctx = await browser.newContext({ colorScheme: 'dark', viewport: { width: 1440, height: 1000 } });
  let page = await ctx.newPage();
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));
  await page.goto(URL); await page.waitForTimeout(700);
  await page.screenshot({ path: DIR + '/t01-login-dark.png' });
  await enter(page);
  await step('тёмная тема: фон тёмный, текст светлый', async () => {
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    if (bg.match(/\d+/g).map(Number)[0] > 90) throw new Error('фон не тёмный: ' + bg);
    const c = await page.evaluate(() => getComputedStyle(document.querySelector('h1')).color);
    if (c.match(/\d+/g).map(Number)[0] < 150) throw new Error('заголовок тёмный на тёмном: ' + c);
  });
  await page.screenshot({ path: DIR + '/t02-dashboard-dark.png', fullPage: true });
  await ctx.close();

  // Явная светлая тема поверх тёмной системы
  ctx = await browser.newContext({ colorScheme: 'dark', viewport: { width: 1200, height: 900 } });
  page = await ctx.newPage();
  await page.goto(URL);
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));
  await page.waitForTimeout(400);
  await step('выбор светлой темы перебивает тёмную систему', async () => {
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    if (bg.match(/\d+/g).map(Number)[0] < 200) throw new Error('осталась тёмной: ' + bg);
  });
  await ctx.close();

  // Телефон
  ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  page = await ctx.newPage();
  page.on('pageerror', (e) => errors.push('MOBILE PAGEERROR: ' + e.message));
  await page.goto(URL); await page.waitForTimeout(700);
  await step('телефон: экран входа помещается', async () => {
    const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (over > 2) throw new Error('выход за экран на ' + over + 'px');
  });
  await page.screenshot({ path: DIR + '/t03-login-mobile.png' });
  await enter(page);
  await step('телефон: нет горизонтальной прокрутки на всех экранах', async () => {
    for (const hash of ['#/dashboard', '#/projects', '#/kanban', '#/calendar', '#/visits', '#/reports', '#/users', '#/dictionaries', '#/audit', '#/bin', '#/fields', '#/settings']) {
      await page.evaluate((x) => { location.hash = x; }, hash);
      await page.waitForTimeout(400);
      const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (over > 2) throw new Error(hash + ' выходит за экран на ' + over + 'px');
    }
  });
  await step('телефон: меню открывается', async () => {
    await page.evaluate(() => { location.hash = '#/dashboard'; });
    await page.waitForTimeout(400);
    await page.locator('.burger').click();
    await page.waitForTimeout(300);
    if (!await page.locator('.sidebar.open').count()) throw new Error('меню не открылось');
    await page.locator('.nav a[href="#/projects"]').click();
    await page.waitForTimeout(500);
  });
  await page.screenshot({ path: DIR + '/t04-registry-mobile.png' });
  await ctx.close();

  console.log('--- ошибки ---');
  errors.forEach((e) => console.log(e));
  console.log(errors.length ? 'ВСЕГО ОШИБОК: ' + errors.length : 'ОШИБОК НЕТ');
  await browser.close();
})();
