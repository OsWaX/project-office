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
  const mode = (m) => fetch('http://localhost:8731/mode/' + m);
  const doc = async () => (await fetch('http://localhost:8731/doc')).text();

  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('CONSOLE: ' + m.text()); });

  await page.goto(URL);
  await page.waitForTimeout(600);
  await page.locator('.login-form select').selectOption({ index: 1 });
  await page.waitForTimeout(250);
  await page.locator('.login-form input[type=password]').fill('Tekstil2026');
  await page.locator('.login-form button[type=submit]').click();
  await page.waitForTimeout(1600);

  await step('этап дорожной карты добавляется и отмечается', async () => {
    await page.evaluate(() => { location.hash = '#/projects/1'; });
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: '+ Этап' }).click();
    await page.waitForTimeout(300);
    await page.locator('.modal input[type=text]').fill('Подписание годовой спецификации');
    await page.getByRole('button', { name: 'Добавить' }).click();
    await page.waitForTimeout(1600);
    if (await page.locator('.step-row').count() !== 1) throw new Error('этап не добавлен');
    await page.locator('.step-check').first().click();
    await page.waitForTimeout(1600);
    if (!await page.locator('.step-check.done').count()) throw new Error('этап не отмечен');
    if (!(await doc()).includes('"state":"done"')) throw new Error('отметка не сохранена');
  });

  await step('визит с программой встреч', async () => {
    await page.evaluate(() => { location.hash = '#/visits'; });
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: '+ Новый визит' }).click();
    await page.waitForTimeout(300);
    await page.locator('.modal select').nth(1).selectOption({ label: 'Германия' });
    await page.locator('.modal input[type=text]').fill('Гамбург, Дюссельдорф');
    await page.locator('.modal textarea').first().fill('Участие в выставке Heimtextil и переговоры с покупателями.');
    await page.getByRole('button', { name: 'Создать визит' }).click();
    await page.waitForTimeout(1600);
    if (!(await page.textContent('h1')).includes('Гамбург')) throw new Error('визит не создан');
    await page.getByRole('button', { name: '+ Встреча' }).click();
    await page.waitForTimeout(300);
    await page.locator('.modal select').first().selectOption({ index: 1 });
    await page.waitForTimeout(200);
    await page.locator('.modal input[type=text]').nth(1).fill('Офис компании, Гамбург');
    await page.getByRole('button', { name: 'Добавить' }).click();
    await page.waitForTimeout(1600);
    if (await page.locator('.agenda-item').count() !== 1) throw new Error('встреча не добавлена в программу');
    if (!await page.locator('.agenda-day').count()) throw new Error('программа не сгруппирована по дням');
  });
  await page.screenshot({ path: DIR + '/r10-visit.png', fullPage: true });

  await step('доска проектов: перенос меняет статус', async () => {
    await page.evaluate(() => { location.hash = '#/kanban'; });
    await page.waitForTimeout(600);
    if (await page.locator('.kanban-col').count() < 7) throw new Error('нет колонок');
    const before = await page.locator('.kanban-col').nth(0).locator('.kanban-card').count();
    await page.evaluate(() => {
      const card = document.querySelector('.kanban-card');
      const target = document.querySelectorAll('.kanban-col')[3];
      const dt = new DataTransfer();
      card.dispatchEvent(new DragEvent('dragstart', { bubbles: true, dataTransfer: dt }));
      target.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }));
      target.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
    });
    await page.waitForTimeout(1600);
    const after = await page.locator('.kanban-col').nth(0).locator('.kanban-card').count();
    if (after !== before - 1) throw new Error('карточка не переехала');
    if (!(await doc()).includes('на доске проектов')) throw new Error('перенос не записан в аудит');
  });
  await page.screenshot({ path: DIR + '/r11-kanban.png', fullPage: true });

  await step('календарь показывает сроки и визиты', async () => {
    await page.evaluate(() => { location.hash = '#/calendar'; });
    await page.waitForTimeout(600);
    if (await page.locator('.cal-cell').count() !== 42) throw new Error('нет сетки месяца');
    // сроки и визиты созданы со смещением вперёд — смотрим следующий месяц
    await page.getByRole('button', { name: /→$/ }).click();
    await page.waitForTimeout(500);
    const events = await page.locator('.cal-event').count();
    if (!events) throw new Error('нет событий в следующем месяце');
    const list = await page.textContent('body');
    if (!list.includes('События месяца')) throw new Error('нет списка событий');
  });

  await step('отчёты считают показатели', async () => {
    await page.evaluate(() => { location.hash = '#/reports'; });
    await page.waitForTimeout(600);
    const body = await page.textContent('body');
    if (!body.includes('Показатели работы проектных менеджеров')) throw new Error('нет сводки по менеджерам');
    if (!await page.locator('.kpi').count()) throw new Error('нет показателей выборки');
  });

  // --- Отказы записи ---
  await step('доступ только на просмотр: предупреждение и отказ', async () => {
    await mode('not_writer');
    await page.evaluate(() => { location.hash = '#/settings'; });
    await page.waitForTimeout(500);
    await page.locator('input[type=number]').first().fill('60');
    await page.getByRole('button', { name: 'Сохранить настройки' }).click();
    await page.waitForTimeout(1200);
    const toast = await page.locator('.toast').textContent();
    if (!toast.includes('только на просмотр')) throw new Error('нет предупреждения: ' + toast);
    if (!await page.locator('.access-strip').count()) throw new Error('нет полосы режима просмотра');
    if ((await doc()).includes('"staleDays":60')) throw new Error('данные записались вопреки отказу');
  });
  await page.screenshot({ path: DIR + '/r12-readonly.png', fullPage: true });

  await step('в режиме просмотра кнопки изменения скрыты', async () => {
    await page.evaluate(() => { location.hash = '#/projects'; });
    await page.waitForTimeout(500);
    if (await page.getByRole('button', { name: '+ Новая запись' }).count()) throw new Error('кнопка создания активна');
  });

  await step('конфликт: сообщение о чужом сохранении', async () => {
    await mode('conflict');
    await page.reload();
    await page.waitForTimeout(900);
    await page.evaluate(() => { location.hash = '#/settings'; });
    await page.waitForTimeout(500);
    await page.locator('input[type=number]').first().fill('55');
    await page.getByRole('button', { name: 'Сохранить настройки' }).click();
    await page.waitForTimeout(1200);
    const toast = await page.locator('.toast').textContent();
    if (!toast.includes('Коллега')) throw new Error('нет сообщения о конфликте: ' + toast);
  });

  await step('слишком частое сохранение', async () => {
    await mode('rate_limited');
    await page.reload();
    await page.waitForTimeout(900);
    await page.evaluate(() => { location.hash = '#/settings'; });
    await page.waitForTimeout(500);
    await page.locator('input[type=number]').first().fill('50');
    await page.getByRole('button', { name: 'Сохранить настройки' }).click();
    await page.waitForTimeout(1200);
    const toast = await page.locator('.toast').textContent();
    if (!toast.includes('частые')) throw new Error('нет сообщения о частоте: ' + toast);
  });

  await mode('ok');

  await step('страница вне claude.ai честно предупреждает', async () => {
    const bare = await browser.newPage();
    const errs = [];
    bare.on('pageerror', (e) => errs.push(e.message));
    await bare.goto(URL + '?nomock=1');
    await bare.waitForTimeout(1200);
    await bare.locator('.login-form select').selectOption({ index: 1 });
    await bare.waitForTimeout(250);
    await bare.locator('.login-form input[type=password]').fill('Tekstil2026');
    await bare.locator('.login-form button[type=submit]').click();
    await bare.waitForTimeout(1200);
    const strip = await bare.locator('.access-strip').count();
    if (!strip) throw new Error('нет предупреждения об отсутствии сохранения');
    const text = await bare.locator('.access-strip').textContent();
    if (!text.includes('не сохраняются')) throw new Error('текст: ' + text);
    if (errs.length) throw new Error('ошибки страницы: ' + errs.join('; '));
    await bare.close();
  });

  console.log('--- ошибки ---');
  errors.forEach((e) => console.log(e));
  console.log(errors.length ? 'ВСЕГО ОШИБОК: ' + errors.length : 'ОШИБОК НЕТ');
  await browser.close();
})();
