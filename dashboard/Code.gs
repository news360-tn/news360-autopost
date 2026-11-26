/**
 * News360 team dashboard - the private store + login (Google Apps Script web app).
 * owner 26 Nov: view-only dashboard for all pages (Instagram, Facebook, YouTube). Nothing here touches the posting workflows.
 *
 * Script properties (Project Settings > Script properties) - set by the owner, never in the page or in GitHub:
 *   DASH_USER + DASH_PASS   one shared login            (or)
 *   DASH_USERS              a login per person: "siva:password1,team1:password2"  (no comma or colon inside a password)
 *   DASH_WRITE_KEY          long random text; the collector (GitHub Actions) sends numbers with it
 * Deploy > New deployment > Web app > Execute as: Me > Who has access: Anyone  (without a correct login the page shows nothing).
 * Files in this project: Code.gs (this file) and Index.html (the page).
 */
var DATA_FILE = 'news360-dashboard-data.json';
var MAX_FAILS = 5;
var LOCK_SECONDS = 900;
var TOKEN_HOURS = 12;

function prop_(k) { return (PropertiesService.getScriptProperties().getProperty(k) || '').trim(); }

function users_() {
  var list = {};
  prop_('DASH_USERS').split(',').forEach(function (x) {
    var i = x.indexOf(':');
    if (i > 0) list[x.slice(0, i).trim()] = x.slice(i + 1).trim();
  });
  if (prop_('DASH_USER') && prop_('DASH_PASS')) list[prop_('DASH_USER')] = prop_('DASH_PASS');
  return list;
}

function same_(a, b) {            // compare without stopping at the first different character
  a = String(a); b = String(b);
  var d = a.length ^ b.length;
  for (var i = 0; i < Math.max(a.length, b.length); i++) d |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return d === 0;
}

function sign_(msg) {
  var key = prop_('DASH_WRITE_KEY') + '|dash-token';
  var sig = Utilities.computeHmacSha256Signature(msg, key);
  return Utilities.base64EncodeWebSafe(sig);
}

function makeToken_(user) {
  var exp = Date.now() + TOKEN_HOURS * 3600 * 1000;
  var body = Utilities.base64EncodeWebSafe(user + '|' + exp);
  return body + '.' + sign_(body);
}

function checkToken_(token) {
  token = String(token || '');
  var i = token.indexOf('.');
  if (i < 1 || !prop_('DASH_WRITE_KEY')) return '';
  var body = token.slice(0, i);
  if (!same_(token.slice(i + 1), sign_(body))) return '';
  var parts = Utilities.newBlob(Utilities.base64DecodeWebSafe(body)).getDataAsString().split('|');
  if (parts.length < 2 || Number(parts[parts.length - 1]) < Date.now()) return '';
  return parts.slice(0, -1).join('|');
}

/** called by the page: login(user, pass) -> {ok, token, user} or {ok:false, error} */
function login(user, pass) {
  var cache = CacheService.getScriptCache();
  var id = 'fail_' + String(user || '').toLowerCase().replace(/[^a-z0-9_.-]/g, '').slice(0, 40);
  var fails = Number(cache.get(id) || 0);
  if (fails >= MAX_FAILS) return { ok: false, error: 'Too many wrong tries. Try again in 15 minutes.' };
  var all = users_();
  var ok = false;
  Object.keys(all).forEach(function (u) { if (same_(u, user) && same_(all[u], pass)) ok = true; });
  if (!ok || !prop_('DASH_WRITE_KEY')) {
    cache.put(id, String(fails + 1), LOCK_SECONDS);
    return { ok: false, error: 'Wrong username or password.' };
  }
  cache.remove(id);
  return { ok: true, token: makeToken_(String(user)), user: String(user) };
}

function dataFile_() {
  var it = DriveApp.getFilesByName(DATA_FILE);
  return it.hasNext() ? it.next() : null;
}

/** called by the page: getData(token) -> the collector's file as text, or '' */
function getData(token) {
  if (!checkToken_(token)) return JSON.stringify({ error: 'login' });
  var f = dataFile_();
  return f ? f.getBlob().getDataAsString() : JSON.stringify({ posts: [], pages: {}, updated: '', notes: { all: 'No data yet - the collector has not sent numbers.' } });
}

/** the collector (GitHub Actions) sends {"action":"put","key":...,"data":{...}} */
function doPost(e) {
  try {
    var b = JSON.parse(e.postData.contents);
    // owner 26 Nov: the page on its own address (Cloudflare Worker) asks the store the same two questions the Apps Script page does
    if (b.action === 'login') return out_(login(String(b.user || ''), String(b.pass || '')));
    if (b.action === 'data') return ContentService.createTextOutput(getData(b.token)).setMimeType(ContentService.MimeType.JSON);
    if (b.action !== 'put' || !prop_('DASH_WRITE_KEY') || !same_(b.key || '', prop_('DASH_WRITE_KEY'))) return out_({ ok: false, error: 'refused' });
    var text = JSON.stringify(b.data);
    var f = dataFile_();
    if (f) f.setContent(text); else DriveApp.createFile(DATA_FILE, text, MimeType.PLAIN_TEXT);
    return out_({ ok: true, bytes: text.length });
  } catch (err) {
    return out_({ ok: false, error: 'bad request' });
  }
}

function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index').setTitle('News360 Dashboard')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}
