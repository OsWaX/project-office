const { chromium } = require('playwright');
const URL = 'http://localhost:8731/';
const DIR = '/tmp/claude-0/-home-user-project-office/42be28a2-4cce-5344-a3ec-34dd2a773f53/scratchpad';

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const errors = [];
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('CONSOLE: ' + m.text()); });
  const step = async (name, fn) => {
    const before = errors.length;
    try { await fn(); } catch (e) { errors.push('STEP ' + name + ': ' + e.message); }
    console.log((errors.length > before ? 'FAIL ' : ' ok  ') + name);
  };
  const doc = async () => (await fetch('http://localhost:8731/doc')).text();
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  await fetch('http://localhost:8731/reset');
  await page.goto(URL);
  await page.waitForTimeout(600);

  await step('первый запуск: экран входа с администратором', async () => {
    if (!await page.locator('.login-page').count()) throw new Error('нет экрана входа');
    const opts = await page.locator('.login-form select option').allTextContents();
    if (!opts.some((o) => o.includes('Администратор'))) throw new Error('нет админа: ' + opts.join('|'));
  });
  await page.screenshot({ path: DIR + '/r01-login.png' });

  await step('первый вход: задаётся код доступа', async () => {
    await page.locator('.login-form select').selectOption({ index: 1 });
    await page.waitForTimeout(200);
    const label = await page.locator('.login-form button[type=submit]').textContent();
    if (label.trim() !== 'Продолжить') throw new Error('кнопка: ' + label);
    await page.locator('.login-form button[type=submit]').click();
    await page.waitForTimeout(300);
    if (!await page.locator('.modal').count()) throw new Error('нет окна создания кода');
    await page.locator('.modal input[type=password]').nth(0).fill('Tekstil2026');
    await page.locator('.modal input[type=password]').nth(1).fill('Tekstil2026');
    await page.getByRole('button', { name: 'Сохранить и войти' }).click();
    await page.waitForTimeout(1500);   // публикация + перезагрузка
    if (!await page.locator('.sidebar').count()) throw new Error('не вошли в систему');
  });

  await step('код доступа сохранён как хеш, самого кода в данных нет', async () => {
    const d = await doc();
    if (d.includes('Tekstil2026')) throw new Error('код доступа сохранён в открытом виде!');
    if (!/"pinHash":"[0-9a-f]{64}"/.test(d)) throw new Error('нет хеша кода');
    if (!/"pinSalt":"[0-9a-f]{32}"/.test(d)) throw new Error('нет соли');
  });

  await step('короткий код отклоняется', async () => {
    // проверяем правило на форме смены кода в личном кабинете
    await page.evaluate(() => { location.hash = '#/profile'; });
    await page.waitForTimeout(400);
    await page.locator('.card input[type=password]').nth(0).fill('Tekstil2026');
    await page.locator('.card input[type=password]').nth(1).fill('123');
    await page.locator('.card input[type=password]').nth(2).fill('123');
    await page.getByRole('button', { name: 'Сохранить' }).click();
    await page.waitForTimeout(400);
    const text = await page.locator('.callout.danger').textContent();
    if (!text.includes('шести')) throw new Error('нет запрета короткого кода: ' + text);
  });

  await step('пустая система: дашборд без записей', async () => {
    await page.evaluate(() => { location.hash = '#/dashboard'; });
    await page.waitForTimeout(400);
    const kpi = await page.locator('.kpi .value').first().textContent();
    if (kpi.trim() !== '0') throw new Error('ожидался ноль записей, получено ' + kpi);
  });
  await page.screenshot({ path: DIR + '/r02-empty.png', fullPage: true });

  await step('создание компании сохраняется', async () => {
    await page.evaluate(() => { location.hash = '#/companies'; });
    await page.waitForTimeout(400);
    await page.getByRole('button', { name: '+ Новая компания' }).click();
    await page.waitForTimeout(300);
    await page.locator('.modal input[type=text]').first().fill('Textilhandel Nord GmbH');
    await page.locator('.modal select').first().selectOption({ label: 'Германия' });
    await page.locator('.modal input[type=text]').nth(1).fill('Гамбург');
    await page.locator('.modal input[type=text]').nth(2).fill('Оптовая торговля текстилем');
    await page.getByRole('button', { name: 'Создать' }).click();
    await page.waitForTimeout(1500);
    const d = await doc();
    if (!d.includes('Textilhandel Nord GmbH')) throw new Error('компания не сохранилась');
  });

  await step('полный список стран доступен', async () => {
    await page.evaluate(() => { location.hash = '#/companies'; });
    await page.waitForTimeout(400);
    await page.getByRole('button', { name: '+ Новая компания' }).click();
    await page.waitForTimeout(300);
    const n = await page.locator('.modal select').first().locator('option').count();
    if (n < 95) throw new Error('стран в списке: ' + n);
    const names = await page.locator('.modal select').first().locator('option').allTextContents();
    ['Франция', 'Бразилия', 'Вьетнам', 'Узбекистан'].forEach((c) => {
      if (!names.includes(c)) throw new Error('нет страны ' + c);
    });
    await page.locator('.modal .icon-btn').click();
    await page.waitForTimeout(200);
  });

  await step('создание проекта сохраняется', async () => {
    await page.evaluate(() => { location.hash = '#/projects'; });
    await page.waitForTimeout(400);
    await page.getByRole('button', { name: '+ Новая запись' }).click();
    await page.waitForTimeout(300);
    await page.locator('.modal input[type=text]').first().fill('Поставка домашнего текстиля в Германию');
    await page.locator('.modal textarea').first().fill('Годовой контракт на поставку комплектов постельного белья.');
    await page.locator('.modal input[type=number]').fill('4200000');
    await page.getByRole('button', { name: 'Создать запись' }).click();
    await page.waitForTimeout(1500);
    const d = await doc();
    if (!d.includes('Поставка домашнего текстиля в Германию')) throw new Error('проект не сохранился');
    if (!await page.locator('h1').textContent().then((t) => t.includes('Германию'))) throw new Error('не открылась карточка');
  });
  await page.screenshot({ path: DIR + '/r03-project.png', fullPage: true });

  await step('данные переживают перезагрузку и видны в новой вкладке', async () => {
    const page2 = await browser.newPage();
    await page2.goto(URL);
    await page2.waitForTimeout(600);
    // другая вкладка — сеанс не общий, но данные те же
    const opts = await page2.locator('.login-form select option').allTextContents();
    if (!opts.some((o) => o.includes('Администратор'))) throw new Error('нет пользователя во второй вкладке');
    await page2.locator('.login-form select').selectOption({ index: 1 });
    await page2.waitForTimeout(200);
    await page2.locator('.login-form input[type=password]').fill('Tekstil2026');
    await page2.locator('.login-form button[type=submit]').click();
    await page2.waitForTimeout(1500);
    await page2.evaluate(() => { location.hash = '#/projects'; });
    await page2.waitForTimeout(500);
    const rows = await page2.locator('table.registry tbody tr').count();
    if (rows !== 1) throw new Error('во второй вкладке записей: ' + rows);
    await page2.close();
  });

  await step('неверный код доступа не пускает', async () => {
    const page3 = await browser.newPage();
    await page3.goto(URL);
    await page3.waitForTimeout(600);
    await page3.locator('.login-form select').selectOption({ index: 1 });
    await page3.waitForTimeout(200);
    await page3.locator('.login-form input[type=password]').fill('неверный');
    await page3.locator('.login-form button[type=submit]').click();
    await page3.waitForTimeout(800);
    const err = await page3.locator('.login-form .callout.danger').textContent();
    if (!err.includes('Неверный')) throw new Error('пустил с неверным кодом');
    if (await page3.locator('.sidebar').count()) throw new Error('вошёл несмотря на неверный код');
    await page3.close();
  });

  console.log('--- ошибки ---');
  errors.forEach((e) => console.log(e));
  console.log(errors.length ? 'ВСЕГО ОШИБОК: ' + errors.length : 'ОШИБОК НЕТ');
  await browser.close();
})();
