# Проверки портала

```bash
node server.js &          # стенд на http://localhost:8731
node t1.js                # вход, код доступа, общие данные
node t2.js                # права ролей, админ-разделы, заявки
node t3.js                # экраны и отказы записи
node t4.js                # тёмная тема и телефон
node t5.js                # дополнение № 1: партнёры и регионы
```

Стенд подменяет возможность `artifact`: публикация сохраняет документ и
перезагружает страницу, как в claude.ai. `/mode/not_writer`, `/mode/conflict`,
`/mode/rate_limited` включают отказы записи, `/reset` возвращает пустую систему,
`?nomock=1` открывает страницу без `window.claude`.

Требуется Playwright и Chromium в `/opt/pw-browsers/chromium`.
