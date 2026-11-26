import fs from 'fs'; import vm from 'vm'; import crypto from 'crypto';
const dir = process.argv[2] || new URL('.', import.meta.url).pathname;
// --- the store (Code.gs) in a stand-in for Google
let props = {DASH_USERS: 'siva:abc123', DASH_WRITE_KEY: 'k'.repeat(40)}, cache = {}, file = null;
const ctx = {
  PropertiesService: {getScriptProperties: () => ({getProperty: k => props[k] || null})},
  CacheService: {getScriptCache: () => ({get: k => cache[k] || null, put: (k, v) => { cache[k] = v; }, remove: k => { delete cache[k]; }})},
  Utilities: {computeHmacSha256Signature: (m, k) => Array.from(crypto.createHmac('sha256', k).update(m).digest()),
    base64EncodeWebSafe: x => Buffer.from(x).toString('base64url'), base64DecodeWebSafe: s => Array.from(Buffer.from(s, 'base64url')),
    newBlob: b => ({getDataAsString: () => Buffer.from(b).toString()})},
  DriveApp: {getFilesByName: () => ({hasNext: () => !!file, next: () => ({getBlob: () => ({getDataAsString: () => file}), setContent: t => { file = t; }})}),
             createFile: (n, t) => { file = t; }},
  MimeType: {PLAIN_TEXT: 'text/plain'},
  ContentService: {MimeType: {JSON: 'json'}, createTextOutput: t => ({t, setMimeType() { return this; }})},
  HtmlService: {}, Date, Math, Object, String, Number, JSON,
};
vm.createContext(ctx); vm.runInContext(fs.readFileSync(dir + '/Code.gs', 'utf8'), ctx);
// --- the website file, with fetch to the store wired to Code.gs doPost
const src = fs.readFileSync(dir + '/worker.js', 'utf8');
const mod = await import('data:text/javascript;base64,' + Buffer.from(src).toString('base64'));
globalThis.fetch = async (url, init) => new Response(ctx.doPost({postData: {contents: init.body}}).t);
const W = mod.default, env = {DASH_URL: 'https://script.example/exec'};
const call = (path, body, method, e) => W.fetch(new Request('https://news360-backend.pages.dev' + path, {method: method || 'POST', body: body ? JSON.stringify(body) : undefined}), e || env);
const t = (n, ok) => { console.log((ok ? 'PASS ' : 'FAIL ') + n); if (!ok) process.exitCode = 1; };
// collector puts data
ctx.doPost({postData: {contents: JSON.stringify({action: 'put', key: 'k'.repeat(40), data: {posts: [{id: 1}], pages: {}, updated: 'x'}})}});
let r = await call('/', null, 'GET'); let h = await r.text(); const r2 = await call('/erode', null, 'GET'); t('district link served', r2.status === 200 && (await r2.text()).includes('News360')); t('file paths not served', (await call('/x.php', null, 'GET')).status === 404);
t('home page served', r.status === 200 && h.includes('News360') && r.headers.get('content-security-policy'));
t('page does not contain the store link', !h.includes('script.example'));
r = await call('/api/login', {user: 'siva', pass: 'abc123'}); let j = await r.json(); t('login works through the website', j.ok && j.token);
let d = await (await call('/api/data', {token: j.token})).json(); t('data arrives with the token', d.posts && d.posts.length === 1);
d = await (await call('/api/data', {token: 'bad.token'})).json(); t('bad token gets nothing', d.error === 'login' && !d.posts);
j = await (await call('/api/login', {user: 'siva', pass: 'nope'})).json(); t('wrong password refused', !j.ok);
r = await call('/api/put', {key: 'k'.repeat(40)}); t('nothing else is passed through (no write via website)', r.status === 404);
r = await call('/api/login', {user: 'siva', pass: 'abc123'}, 'POST', {}); t('missing DASH_URL explained', r.status === 500);
r = await W.fetch(new Request('https://x/api/login', {method: 'POST', body: 'x'.repeat(3000)}), env); t('oversized request refused', r.status === 413);
