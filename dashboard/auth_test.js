const crypto = require('crypto'), fs = require('fs'), vm = require('vm');
let props = {DASH_USER: 'owner360', DASH_PASS: 'Pa$$word-123!', DASH_USERS: 'siva:abc123,team1:xyz789', DASH_WRITE_KEY: 'k'.repeat(40)};
let cache = {};
const ctx = {
  PropertiesService: {getScriptProperties: () => ({getProperty: k => props[k] || null})},
  CacheService: {getScriptCache: () => ({get: k => cache[k] || null, put: (k, v) => { cache[k] = v; }, remove: k => { delete cache[k]; }})},
  Utilities: {
    computeHmacSha256Signature: (msg, key) => Array.from(crypto.createHmac('sha256', key).update(msg).digest()),
    base64EncodeWebSafe: x => (typeof x === 'string' ? Buffer.from(x) : Buffer.from(x)).toString('base64url'),
    base64DecodeWebSafe: s => Array.from(Buffer.from(s, 'base64url')),
    newBlob: bytes => ({getDataAsString: () => Buffer.from(bytes).toString()}),
  },
  DriveApp: {getFilesByName: () => ({hasNext: () => false})}, HtmlService: {}, ContentService: {}, MimeType: {}, Date, Math, Object, String, Number, JSON,
};
vm.createContext(ctx); vm.runInContext(fs.readFileSync(__dirname + '/Code.gs', 'utf8'), ctx);
const t = (name, ok) => { console.log((ok ? 'PASS ' : 'FAIL ') + name); if (!ok) process.exitCode = 1; };
let r = ctx.login('owner360', 'Pa$$word-123!'); t('shared login works', r.ok && r.token);
t('token verifies', ctx.checkToken_(r.token) === 'owner360');
t('per-person login works', ctx.login('siva', 'abc123').ok);
t('wrong password refused', !ctx.login('siva', 'nope').ok);
t('unknown user refused', !ctx.login('ghost', 'x').ok);
t('tampered token refused', ctx.checkToken_(r.token.slice(0, -2) + 'AA') === '' && ctx.checkToken_('x.y') === '' && ctx.checkToken_('') === '');
const expired = (() => { const exp = Date.now() - 1000, body = Buffer.from('siva|' + exp).toString('base64url'); return body + '.' + ctx.sign_(body); })();
t('expired token refused', ctx.checkToken_(expired) === '');
t('getData refuses a bad token', JSON.parse(ctx.getData('bad')).error === 'login');
for (let i = 0; i < 5; i++) ctx.login('team1', 'wrong');
t('locked after 5 wrong tries', /Too many/.test(ctx.login('team1', 'xyz789').error || ''));
t('other user unaffected by the lock', ctx.login('siva', 'abc123').ok);
props.DASH_WRITE_KEY = ''; t('no write key = no login at all', !ctx.login('siva', 'abc123').ok);
