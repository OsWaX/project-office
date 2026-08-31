// Стенд, повторяющий работу артефакта: publish сохраняет документ, страница
// перезагружается на новую версию; можно включить отказ в записи и конфликт.
const http = require('http');
const fs = require('fs');

const SRC = '/home/user/project-office/portal/index.html';
const SKELETON = (body) => `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{color-scheme:light dark}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style>
</head><body>${body}</body></html>`;

let current = SKELETON(fs.readFileSync(SRC, 'utf8'));
let mode = 'ok';            // ok | not_writer | conflict | rate_limited
let publishes = 0;

const MOCK = `<script>
window.__published = 0;
window.__saved = [];
window.claude = { use: function (name) {
  if (name === 'artifact') return Promise.resolve({ publish: function (html) {
    return fetch('/publish', { method: 'POST', body: html }).then(function (r) {
      return r.json().then(function (res) {
        if (res.error) { var e = new Error(res.error); e.code = res.error; throw e; }
        window.__published++;
        location.reload();
        return new Promise(function () {});   // страница уходит на перезагрузку
      });
    });
  } });
  if (name === 'downloads') return Promise.resolve({ save: function (arg) {
    window.__saved.push(arg); return Promise.resolve({ ok: true });
  } });
  return Promise.resolve(null);
} };
</script>`;

http.createServer((req, res) => {
  if (req.method === 'POST' && req.url === '/publish') {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => {
      const body = Buffer.concat(chunks).toString('utf8');
      publishes++;
      if (mode !== 'ok') { res.end(JSON.stringify({ error: mode })); return; }
      current = body;
      res.end(JSON.stringify({ ok: true }));
    });
    return;
  }
  if (req.url.startsWith('/mode/')) { mode = req.url.split('/')[2]; res.end('mode=' + mode); return; }
  if (req.url === '/reset') {
    current = SKELETON(fs.readFileSync(SRC, 'utf8')); publishes = 0; mode = 'ok';
    res.end('reset'); return;
  }
  if (req.url === '/doc') { res.setHeader('content-type', 'text/plain'); res.end(current); return; }
  if (req.url === '/publishes') { res.end(String(publishes)); return; }
  res.setHeader('content-type', 'text/html; charset=utf-8');
  // ?nomock=1 — страница без window.claude, как при открытии вне claude.ai
  res.end(req.url.indexOf('nomock') !== -1 ? current : current.replace('</head>', MOCK + '</head>'));
}).listen(8731, () => console.log('стенд на http://localhost:8731'));
