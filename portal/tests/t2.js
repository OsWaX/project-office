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
  const doc = async () => (await fetch('http://localhost:8731/doc')).text();

  const login = async (page, index, pin, newPin) => {
    await page.goto(URL);
    await page.waitForTimeout(600);
    await page.locator('.login-form select').selectOption({ index });
    await page.waitForTimeout(250);
    if (newPin) {
      await page.locator('.login-form button[type=submit]').click();
      await page.waitForTimeout(400);
      await page.locator('.modal input[type=password]').nth(0).fill(newPin);
      await page.locator('.modal input[type=password]').nth(1).fill(newPin);
      await page.getByRole('button', { name: 'Сохранить и войти' }).click();
    } else {
      await page.locator('.login-form input[type=password]').fill(pin);
      await page.locator('.login-form button[type=submit]').click();
    }
    await page.waitForTimeout(1600);
  };

  const admin = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  admin.on('pageerror', (e) => errors.push('ADMIN PAGEERROR: ' + e.message));
  admin.on('console', (m) => { if (m.type() === 'error') errors.push('ADMIN CONSOLE: ' + m.text()); });
  await login(admin, 1, 'Tekstil2026');

  await step('администратор видит все админ-разделы', async () => {
    for (const path of ['/users', '/fields', '/dictionaries', '/settings', '/audit', '/bin']) {
      if (!await admin.locator('.nav a[href="#' + path + '"]').count()) throw new Error('нет пункта ' + path);
    }
  });

  await step('создание проектного менеджера', async () => {
    await admin.evaluate(() => { location.hash = '#/users'; });
    await admin.waitForTimeout(500);
    await admin.getByRole('button', { name: '+ Новый сотрудник' }).click();
    await admin.waitForTimeout(300);
    await admin.locator('.modal input[type=text]').nth(0).fill('Каримова Дилноза Шухратовна');
    await admin.locator('.modal input[type=text]').nth(1).fill('Проектный менеджер по Европе');
    await admin.locator('.modal select').nth(0).selectOption('team');
    await admin.locator('.modal select').nth(1).selectOption('europe');
    await admin.getByRole('button', { name: 'Добавить' }).click();
    await admin.waitForTimeout(1600);
    const d = await doc();
    if (!d.includes('Каримова Дилноза')) throw new Error('сотрудник не сохранён');
    if (!/"pinHash":null/.test(d)) throw new Error('у нового сотрудника должен отсутствовать код');
  });
  await admin.screenshot({ path: DIR + '/r04-users.png', fullPage: true });

  await step('справочник отраслей пополняется', async () => {
    await admin.evaluate(() => { location.hash = '#/dictionaries?tab=sectors'; });
    await admin.waitForTimeout(500);
    const before = await admin.locator('table.data tbody tr').count();
    await admin.getByRole('button', { name: '+ Добавить' }).click();
    await admin.waitForTimeout(300);
    await admin.locator('.modal input[type=text]').fill('Ковровые изделия');
    await admin.getByRole('button', { name: 'Сохранить' }).click();
    await admin.waitForTimeout(1600);
    const after = await admin.locator('table.data tbody tr').count();
    if (after !== before + 1) throw new Error('отрасль не добавилась: ' + before + ' -> ' + after);
  });

  await step('новая отрасль появляется в форме проекта', async () => {
    await admin.evaluate(() => { location.hash = '#/projects'; });
    await admin.waitForTimeout(500);
    await admin.getByRole('button', { name: '+ Новая запись' }).click();
    await admin.waitForTimeout(300);
    const opts = await admin.locator('.modal select').nth(1).locator('option').allTextContents();
    if (!opts.includes('Ковровые изделия')) throw new Error('нет новой отрасли: ' + opts.join('|'));
    await admin.locator('.modal .icon-btn').click();
    await admin.waitForTimeout(200);
  });

  await step('конструктор форм: поле и голосование', async () => {
    await admin.evaluate(() => { location.hash = '#/fields'; });
    await admin.waitForTimeout(500);
    await admin.getByRole('button', { name: '+ Новое поле' }).click();
    await admin.waitForTimeout(300);
    await admin.locator('.modal input[type=text]').first().fill('Мера государственной поддержки');
    await admin.locator('.modal select').nth(1).selectOption('select');
    await admin.waitForTimeout(200);
    await admin.locator('.modal textarea').fill('Не требуется\nЭкспортная субсидия\nЛьготный кредит');
    await admin.getByRole('button', { name: 'Сохранить' }).click();
    await admin.waitForTimeout(1600);

    await admin.getByRole('button', { name: '+ Новое поле' }).click();
    await admin.waitForTimeout(300);
    await admin.locator('.modal input[type=text]').first().fill('Приоритет проекта');
    await admin.locator('.modal select').nth(1).selectOption('poll');
    await admin.waitForTimeout(200);
    await admin.locator('.modal textarea').fill('Высокий\nСредний\nНизкий');
    await admin.getByRole('button', { name: 'Сохранить' }).click();
    await admin.waitForTimeout(1600);
    const rows = await admin.locator('table.data tbody tr').count();
    if (rows !== 2) throw new Error('полей: ' + rows);
  });
  await admin.screenshot({ path: DIR + '/r05-fields.png', fullPage: true });

  await step('произвольное поле появляется в форме и карточке', async () => {
    await admin.evaluate(() => { location.hash = '#/projects/1'; });
    await admin.waitForTimeout(500);
    if (!(await admin.textContent('body')).includes('Дополнительные сведения')) throw new Error('нет карточки доп. сведений');
    if (!(await admin.textContent('body')).includes('Приоритет проекта')) throw new Error('нет голосования');
    await admin.getByRole('button', { name: '✎ Изменить' }).click();
    await admin.waitForTimeout(400);
    const labels = await admin.locator('.modal label').allTextContents();
    if (!labels.some((l) => l.includes('Мера государственной поддержки'))) throw new Error('поля нет в форме');
    await admin.locator('.modal select').last().selectOption('Льготный кредит');
    await admin.getByRole('button', { name: 'Сохранить' }).click();
    await admin.waitForTimeout(1600);
    if (!(await doc()).includes('Льготный кредит')) throw new Error('значение не сохранилось');
  });

  await step('голосование учитывает голос', async () => {
    await admin.evaluate(() => { location.hash = '#/projects/1'; });
    await admin.waitForTimeout(500);
    await admin.locator('.chip', { hasText: 'Высокий' }).first().click();
    await admin.waitForTimeout(1600);
    const d = await doc();
    if (!d.includes('"option":"Высокий"')) throw new Error('голос не сохранён');
    if (!(await admin.textContent('body')).includes('проголосовало: 1')) throw new Error('счётчик голосов не обновился');
  });
  await admin.screenshot({ path: DIR + '/r06-project-custom.png', fullPage: true });

  // --- Проектный менеджер ---
  const mgr = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  mgr.on('pageerror', (e) => errors.push('MGR PAGEERROR: ' + e.message));
  await login(mgr, 2, null, 'Yevropa2026');

  await step('менеджер вошёл и не видит админ-разделы', async () => {
    const name = await mgr.locator('.user-chip .u-name').textContent();
    if (!name.includes('Каримова')) throw new Error('вошёл не тот: ' + name);
    for (const path of ['/users', '/fields', '/dictionaries', '/settings', '/audit', '/bin']) {
      if (await mgr.locator('.nav a[href="#' + path + '"]').count()) throw new Error('менеджеру виден ' + path);
    }
  });

  await step('менеджер не может изменить чужую запись, только заявка', async () => {
    await mgr.evaluate(() => { location.hash = '#/projects/1'; });
    await mgr.waitForTimeout(500);
    if (await mgr.getByRole('button', { name: '✎ Изменить' }).count()) throw new Error('есть кнопка изменения');
    if (!await mgr.getByRole('button', { name: /Запросить исправление/ }).count()) throw new Error('нет кнопки заявки');
    if (!await mgr.locator('.step-check').count()) { /* этапов нет — нормально */ }
  });

  await step('менеджер подаёт заявку на исправление', async () => {
    await mgr.getByRole('button', { name: /Запросить исправление/ }).click();
    await mgr.waitForTimeout(400);
    await mgr.locator('.modal select').first().selectOption('amount');
    await mgr.waitForTimeout(250);
    await mgr.locator('.modal input[type=number]').fill('4500000');
    await mgr.locator('.modal textarea').last().fill('Сумма уточнена по подписанной спецификации.');
    await mgr.getByRole('button', { name: 'Отправить заявку' }).click();
    await mgr.waitForTimeout(1600);
    if (!(await doc()).includes('уточнена по подписанной спецификации')) throw new Error('заявка не сохранилась');
  });

  await step('менеджер не может одобрить свою заявку', async () => {
    await mgr.evaluate(() => { location.hash = '#/corrections'; });
    await mgr.waitForTimeout(500);
    if (await mgr.getByRole('button', { name: 'Одобрить' }).count()) throw new Error('менеджер может одобрять');
  });
  await mgr.screenshot({ path: DIR + '/r07-manager.png', fullPage: true });

  await step('администратор одобряет — значение применяется', async () => {
    await admin.reload();
    await admin.waitForTimeout(800);
    await admin.evaluate(() => { location.hash = '#/corrections'; });
    await admin.waitForTimeout(600);
    await admin.getByRole('button', { name: 'Одобрить' }).first().click();
    await admin.waitForTimeout(400);
    await admin.getByRole('button', { name: 'Одобрить и применить' }).click();
    await admin.waitForTimeout(1600);
    const d = await doc();
    if (!d.includes('"amount":4500000')) throw new Error('сумма не изменилась');
    if (!d.includes('Исправление по заявке')) throw new Error('нет записи в аудите');
  });

  await step('удаление в корзину и восстановление', async () => {
    await admin.evaluate(() => { location.hash = '#/projects/1'; });
    await admin.waitForTimeout(500);
    await admin.getByRole('button', { name: 'Удалить' }).click();
    await admin.waitForTimeout(400);
    await admin.getByRole('button', { name: 'Удалить', exact: true }).last().click();
    await admin.waitForTimeout(1600);
    let d = await doc();
    if (!d.includes('"trash"')) throw new Error('нет корзины');
    if (d.includes('"projects":[{')) throw new Error('проект остался в реестре');
    await admin.evaluate(() => { location.hash = '#/bin'; });
    await admin.waitForTimeout(500);
    if (!await admin.getByRole('button', { name: 'Восстановить' }).count()) throw new Error('нечего восстанавливать');
    await admin.getByRole('button', { name: 'Восстановить' }).click();
    await admin.waitForTimeout(1600);
    await admin.evaluate(() => { location.hash = '#/projects'; });
    await admin.waitForTimeout(500);
    const rows = await admin.locator('table.registry tbody tr').count();
    if (rows !== 1) throw new Error('после восстановления записей: ' + rows);
  });
  await admin.screenshot({ path: DIR + '/r08-bin.png', fullPage: true });

  await step('настройки сохраняются', async () => {
    await admin.evaluate(() => { location.hash = '#/settings'; });
    await admin.waitForTimeout(500);
    await admin.locator('input[type=number]').first().fill('45');
    await admin.getByRole('button', { name: 'Сохранить настройки' }).click();
    await admin.waitForTimeout(1600);
    if (!(await doc()).includes('"staleDays":45')) throw new Error('настройка не сохранилась');
  });

  await step('выгрузка CSV работает', async () => {
    await admin.evaluate(() => { location.hash = '#/projects'; });
    await admin.waitForTimeout(500);
    await admin.getByRole('button', { name: /Выгрузить в CSV/ }).click();
    await admin.waitForTimeout(600);
    const saved = await admin.evaluate(() => window.__saved);
    if (!saved.length) throw new Error('файл не сохранён');
    if (saved[0].filename !== 'projects.csv') throw new Error('имя: ' + saved[0].filename);
    if (!saved[0].data.includes('Мера государственной поддержки')) throw new Error('нет колонки произвольного поля');
    if (!saved[0].data.includes('Льготный кредит')) throw new Error('нет значения произвольного поля');
  });

  await step('журнал аудита содержит все действия', async () => {
    await admin.evaluate(() => { location.hash = '#/audit'; });
    await admin.waitForTimeout(600);
    const body = await admin.textContent('table.data tbody');
    ['Добавлен сотрудник', 'Создана запись', 'Создана компания', 'Исправление по заявке',
     'Удалена запись', 'Восстановлена запись', 'Изменены настройки'].forEach((t) => {
      if (!body.includes(t)) throw new Error('нет события: ' + t);
    });
  });
  await admin.screenshot({ path: DIR + '/r09-audit.png', fullPage: true });

  console.log('--- ошибки ---');
  errors.forEach((e) => console.log(e));
  console.log(errors.length ? 'ВСЕГО ОШИБОК: ' + errors.length : 'ОШИБОК НЕТ');
  await browser.close();
})();
