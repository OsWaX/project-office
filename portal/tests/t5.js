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
  const company = async (name, iso) => {
    await page.evaluate(() => { location.hash = '#/companies'; });
    await page.waitForTimeout(400);
    await page.getByRole('button', { name: '+ Новая компания' }).click();
    await page.waitForTimeout(300);
    await page.locator('.modal input[type=text]').first().fill(name);
    await page.locator('.modal select').first().selectOption({ label: iso });
    await page.getByRole('button', { name: 'Создать' }).click();
    await page.waitForTimeout(1500);
  };

  await page.goto(URL);
  await page.waitForTimeout(600);

  await step('экран входа называет ведомство по-новому', async () => {
    const t = await page.locator('.login-hero .ministry').textContent();
    if (!t.includes('Агентство по развитию лёгкой промышленности')) throw new Error('ведомство: ' + t);
  });

  await step('вход и первичная настройка', async () => {
    await page.locator('.login-form select').selectOption({ index: 1 });
    await page.waitForTimeout(250);
    await page.locator('.login-form button[type=submit]').click();
    await page.waitForTimeout(400);
    await page.locator('.modal input[type=password]').nth(0).fill('Tekstil2026');
    await page.locator('.modal input[type=password]').nth(1).fill('Tekstil2026');
    await page.getByRole('button', { name: 'Сохранить и войти' }).click();
    await page.waitForTimeout(1600);
    if (!await page.locator('.sidebar').count()) throw new Error('не вошли');
  });

  await step('без компаний создание проекта подсказывает завести компанию', async () => {
    await page.evaluate(() => { location.hash = '#/projects'; });
    await page.waitForTimeout(400);
    await page.getByRole('button', { name: '+ Новая запись' }).click();
    await page.waitForTimeout(600);
    const toast = await page.locator('.toast.error').last().textContent();
    if (!toast.includes('заведите компанию')) throw new Error('нет подсказки: ' + toast);
    if (await page.locator('.modal').count()) throw new Error('форма открылась без компаний');
  });

  await step('заведены иностранный партнёр и узбекская организация', async () => {
    await company('Anadolu Tekstil A.Ş.', 'Турция');
    await company('АО «Узбектекстиль»', 'Узбекистан');
    await company('СИЭЗ «Наманган»', 'Узбекистан');
    await page.evaluate(() => { location.hash = '#/companies'; });
    await page.waitForTimeout(500);
    const n = await page.locator('table.data tbody tr').count();
    if (n !== 3) throw new Error('компаний: ' + n);
  });

  await step('инвестиционный проект: партнёры и регионы реализации', async () => {
    await page.evaluate(() => { location.hash = '#/projects'; });
    await page.waitForTimeout(400);
    await page.getByRole('button', { name: '+ Новая запись' }).click();
    await page.waitForTimeout(400);
    await page.locator('.modal input[type=text]').first().fill('Совместное прядильное производство в Наманганской области');
    // направление → инвестиции, чтобы появились регионы
    await page.locator('.modal select').nth(2).selectOption('investment');
    await page.waitForTimeout(300);
    await page.locator('.modal input[type=number]').first().fill('28000000');
    // местный партнёр
    await page.getByRole('button', { name: '+ Добавить партнёра' }).click();
    await page.waitForTimeout(200);
    await page.locator('.modal select[name=company_id]').selectOption({ label: 'АО «Узбектекстиль» — Узбекистан' });
    await page.locator('.modal input[name=role_note]').fill('Учредитель совместного предприятия');
    // регион реализации
    await page.getByRole('button', { name: '+ Добавить регион' }).click();
    await page.waitForTimeout(200);
    await page.locator('.modal select[name=region]').selectOption('namangan');
    await page.locator('.modal input[name=locality]').fill('Наманган');
    await page.locator('.modal input[name=amount]').fill('20000000');
    await page.getByRole('button', { name: 'Создать запись' }).click();
    await page.waitForTimeout(1700);
    const d = await doc();
    if (!d.includes('"region":"namangan"')) throw new Error('регион не сохранён');
    if (!d.includes('Учредитель совместного предприятия')) throw new Error('партнёр не сохранён');
  });
  await page.screenshot({ path: DIR + '/u01-project.png', fullPage: true });

  await step('карточка показывает узбекскую сторону', async () => {
    const body = await page.textContent('body');
    if (!body.includes('Иностранный партнёр')) throw new Error('нет иностранного партнёра');
    if (!body.includes('Местные партнёры')) throw new Error('нет местных партнёров');
    if (!body.includes('Регионы реализации в Узбекистане')) throw new Error('нет таблицы регионов');
    if (!body.includes('Наманганская область')) throw new Error('нет названия региона');
  });

  await step('обязательный населённый пункт проверяется', async () => {
    await page.getByRole('button', { name: '✎ Изменить' }).click();
    await page.waitForTimeout(400);
    await page.getByRole('button', { name: '+ Добавить регион' }).click();
    await page.waitForTimeout(200);
    await page.locator('.modal select[name=region]').last().selectOption('fergana');
    await page.getByRole('button', { name: 'Сохранить' }).click();
    await page.waitForTimeout(600);
    const toast = await page.locator('.toast').last().textContent();
    if (!toast.includes('город или район')) throw new Error('нет проверки: ' + toast);
    await page.locator('.modal input[name=locality]').last().fill('Маргилан');
    await page.getByRole('button', { name: 'Сохранить' }).click();
    await page.waitForTimeout(1700);
    if (!(await doc()).includes('Маргилан')) throw new Error('второй регион не сохранён');
  });

  await step('повторный регион отклоняется', async () => {
    await page.getByRole('button', { name: '✎ Изменить' }).click();
    await page.waitForTimeout(400);
    await page.getByRole('button', { name: '+ Добавить регион' }).click();
    await page.waitForTimeout(200);
    await page.locator('.modal select[name=region]').last().selectOption('namangan');
    await page.locator('.modal input[name=locality]').last().fill('Чуст');
    await page.getByRole('button', { name: 'Сохранить' }).click();
    await page.waitForTimeout(600);
    const toast = await page.locator('.toast').last().textContent();
    if (!toast.includes('уже добавлен')) throw new Error('дубль региона прошёл: ' + toast);
    await page.locator('.modal .icon-btn').click();
    await page.waitForTimeout(300);
  });

  await step('дашборд: карта Узбекистана и охват регионов', async () => {
    await page.evaluate(() => { location.hash = '#/dashboard'; });
    await page.waitForTimeout(700);
    const body = await page.textContent('body');
    if (!body.includes('Реализация в Узбекистане')) throw new Error('нет блока');
    if (!body.includes('Регионов Узбекистана охвачено')) throw new Error('нет показателя охвата');
    if (!body.includes('2 из 14')) throw new Error('охват посчитан неверно');
    const shapes = await page.locator('.worldmap .region').count();
    if (shapes !== 14) throw new Error('областей на карте: ' + shapes);
    if (!body.includes('Не распределено по регионам')) throw new Error('нет строки нераспределённого объёма');
  });
  await page.screenshot({ path: DIR + '/u02-dashboard-uz.png', fullPage: true });

  await step('клик по региону фильтрует реестр', async () => {
    await page.evaluate(() => { location.hash = '#/projects?uz_region=namangan'; });
    await page.waitForTimeout(600);
    const rows = await page.locator('table.registry tbody tr').count();
    if (rows !== 1) throw new Error('строк по фильтру: ' + rows);
    await page.evaluate(() => { location.hash = '#/projects?uz_region=bukhara'; });
    await page.waitForTimeout(600);
    if (await page.locator('table.registry tbody tr').count() !== 0) throw new Error('фильтр по пустому региону вернул записи');
  });

  await step('карточка компании: роль узбекской стороны', async () => {
    await page.evaluate(() => { location.hash = '#/companies'; });
    await page.waitForTimeout(500);
    await page.getByRole('link', { name: 'АО «Узбектекстиль»' }).click();
    await page.waitForTimeout(600);
    const body = await page.textContent('body');
    if (!body.includes('узбекская сторона')) throw new Error('нет блока участия');
    if (!body.includes('Учредитель совместного предприятия')) throw new Error('нет роли');
  });

  await step('выгрузка содержит партнёров и регионы', async () => {
    await page.evaluate(() => { location.hash = '#/projects'; });
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /Выгрузить в CSV/ }).click();
    await page.waitForTimeout(600);
    const saved = await page.evaluate(() => window.__saved);
    const csv = saved[saved.length - 1].data;
    if (!csv.includes('Местные партнёры;Регионы реализации')) throw new Error('нет колонок');
    if (!csv.includes('Наманганская область — Наманган')) throw new Error('нет значения региона');
  });

  await step('переключатель регионов для экспортных записей', async () => {
    await page.evaluate(() => { location.hash = '#/settings'; });
    await page.waitForTimeout(500);
    await page.locator('.checkbox input[type=checkbox]').check();
    await page.getByRole('button', { name: 'Сохранить настройки' }).click();
    await page.waitForTimeout(1700);
    if (!(await doc()).includes('"locationsForExport":true')) throw new Error('настройка не сохранилась');
    await page.evaluate(() => { location.hash = '#/projects'; });
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: '+ Новая запись' }).click();
    await page.waitForTimeout(400);
    await page.locator('.modal select').nth(2).selectOption('export');
    await page.waitForTimeout(300);
    const hidden = await page.locator('.modal .hidden .form-section-title', { hasText: 'Регионы реализации' }).count();
    if (hidden) throw new Error('регионы скрыты, хотя настройка включена');
    await page.locator('.modal .icon-btn').click();
    await page.waitForTimeout(200);
  });

  console.log('--- ошибки ---');
  errors.forEach((e) => console.log(e));
  console.log(errors.length ? 'ВСЕГО ОШИБОК: ' + errors.length : 'ОШИБОК НЕТ');
  await browser.close();
})();
