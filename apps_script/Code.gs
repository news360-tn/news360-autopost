/**
 * News360 bridge – runs in the nammarasipuram2805@gmail.com Google account.
 * The GitHub posting job talks to this web app to:
 *   - read the queue of stories from the "News360 Log" Sheet
 *   - get the Instagram tokens (kept here, refreshed automatically every week)
 *   - fetch a recorded human voice for a reel (Drive folder "Voice")
 *   - after posting: update the Sheet + the story's Google Doc and email the owner
 *
 * Setup (once): see README.md in the GitHub repository, section "Apps Script".
 * Script properties used: BRIDGE_KEY, IG_TOKEN_RASIPURAM, IG_TOKEN_NAMAKKAL, (auto) VOICE_FOLDER_ID
 */
var SHEET_ID = '10lKyQo4rPkSyGP6kj3zvVBpm17r5fXzTa6vwdnu3y00';
var TAB = 'News';
var ROOT_FOLDER_ID = '1Nm6KqDoS_mz4T9UKxnvVN69EAibWz55p';
var OWNER_EMAIL = 'nammarasipuram2805@gmail.com';
var SHEET_LINK = 'https://docs.google.com/spreadsheets/d/' + SHEET_ID + '/edit';

// 1-based column numbers in the News tab
var C = {
  story_id: 1, researched: 2, published: 3, headline_ta: 4, headline_en: 5, category: 6, location: 7,
  importance: 8, verification: 9, source: 10, other_sources: 11, review_page: 12, doc: 13, notion: 14,
  caption: 15, email_sent: 16, gmail_id: 17, review: 18, post_to: 19, reel: 20, reel_script: 21,
  slides_spec: 22, post_status: 23, posted_at: 24, rasipuram_link: 25, namakkal_link: 26, reel_link: 27, notes: 28
};
var PAGE_LABEL = { rasipuram: 'இராசிபுரம் 360', namakkal: 'நாமக்கல் 360' };
var PAGE_COL = { rasipuram: C.rasipuram_link, namakkal: C.namakkal_link };

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
function props_() { return PropertiesService.getScriptProperties(); }
function authorized_(e) {
  var key = props_().getProperty('BRIDGE_KEY');
  return key && e && e.parameter && e.parameter.key === key;
}
function sheet_() { return SpreadsheetApp.openById(SHEET_ID).getSheetByName(TAB); }
function nowIst_() { return Utilities.formatDate(new Date(), 'Asia/Kolkata', 'dd MMM yyyy, HH:mm'); }

function doGet(e) {
  if (!authorized_(e)) return json_({ ok: false, error: 'unauthorized' });
  try {
    var a = e.parameter.action;
    if (a === 'queue') return json_({ ok: true, rows: queue_() });
    if (a === 'token') return json_({ ok: true, token: token_(e.parameter.page) });
    if (a === 'voice') return json_(voice_(e.parameter.story));
    if (a === 'ping') return json_({ ok: true, time: nowIst_() });
    return json_({ ok: false, error: 'unknown action ' + a });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

function doPost(e) {
  if (!authorized_(e)) return json_({ ok: false, error: 'unauthorized' });
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var body = JSON.parse(e.postData.contents);
    if (body.action === 'posted') return json_(posted_(body));
    if (body.action === 'error') return json_(error_(body));
    return json_({ ok: false, error: 'unknown action ' + body.action });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

// ------------------------------------------------------------------ queue
function rowObj_(values, rowNum) {
  var o = { row: rowNum };
  for (var k in C) o[k] = String(values[C[k] - 1] || '');
  return o;
}
function targets_(postTo) {
  var s = String(postTo || '').toLowerCase(), out = [];
  if (s.indexOf('rasipuram') >= 0) out.push('rasipuram');
  if (s.indexOf('namakkal') >= 0 || out.length === 0) out.push('namakkal');
  return out;
}
function queue_() {
  var sh = sheet_();
  var last = sh.getLastRow();
  if (last < 2) return [];
  var data = sh.getRange(2, 1, last - 1, 28).getValues();
  var out = [];
  for (var i = 0; i < data.length; i++) {
    var r = rowObj_(data[i], i + 2);
    var st = r.post_status.toLowerCase();
    if (!r.story_id || !r.slides_spec) continue;
    if (st !== 'queued' && st !== 'partly posted' && st !== 'posted') continue;
    if (r.review.toLowerCase() === 'hold') continue;
    var pagesLeft = targets_(r.post_to).filter(function (p) { return !r[p + '_link']; }).length;
    var reelLeft = r.reel.toLowerCase() === 'yes' && !r.reel_link;
    if (pagesLeft === 0 && !reelLeft) continue;
    out.push(r);
  }
  return out;
}

// ------------------------------------------------------------------ tokens
function token_(page) {
  var t = props_().getProperty('IG_TOKEN_' + String(page).toUpperCase());
  if (!t) throw new Error('No Instagram token saved for ' + page);
  return t;
}
/** Runs weekly (trigger made by setup): keeps the 60-day Instagram tokens alive. */
function refreshTokens() {
  ['RASIPURAM', 'NAMAKKAL'].forEach(function (p) {
    var key = 'IG_TOKEN_' + p, t = props_().getProperty(key);
    if (!t) return;
    var res = UrlFetchApp.fetch('https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=' +
      encodeURIComponent(t), { muteHttpExceptions: true });
    var d = JSON.parse(res.getContentText());
    if (d.access_token) {
      props_().setProperty(key, d.access_token);
    } else {
      GmailApp.sendEmail(OWNER_EMAIL, '[NEWS360] Instagram token refresh failed – ' + p,
        'The Instagram token for ' + p + ' could not be refreshed:\n' + res.getContentText() +
        '\n\nPlease generate a new token in the Meta developer app and save it in Apps Script → Project Settings → Script properties (' + key + ').');
    }
  });
}

// ------------------------------------------------------------------ recorded voice
function voiceFolder_() {
  var id = props_().getProperty('VOICE_FOLDER_ID');
  if (id) return DriveApp.getFolderById(id);
  var f = DriveApp.getFolderById(ROOT_FOLDER_ID).createFolder('Voice');
  props_().setProperty('VOICE_FOLDER_ID', f.getId());
  return f;
}
function voice_(story) {
  var it = voiceFolder_().getFiles();
  while (it.hasNext()) {
    var f = it.next(), name = f.getName();
    if (name.toLowerCase().indexOf(String(story).toLowerCase() + '.') === 0 && f.getSize() < 15 * 1024 * 1024) {
      var ext = name.substring(name.lastIndexOf('.'));
      return { ok: true, found: true, name: name, ext: ext, data: Utilities.base64Encode(f.getBlob().getBytes()) };
    }
  }
  return { ok: true, found: false };
}

// ------------------------------------------------------------------ after posting
function hashtags_(caption) {
  return (String(caption).match(/#[^\s#]+/g) || []).join(' ');
}
function posted_(b) {
  var sh = sheet_();
  var vals = sh.getRange(b.row, 1, 1, 28).getValues()[0];
  var r = rowObj_(vals, b.row);
  var label = PAGE_LABEL[b.page] || b.page;
  var kindLabel = b.kind === 'reel' ? 'Reel' : 'Carousel';
  var time = nowIst_();

  if (b.dry_run) {
    appendNote_(sh, b.row, r.notes, time + ' TEST ' + kindLabel + ' ' + label + ' (not posted): ' + (b.media_urls || []).join(' '));
    GmailApp.sendEmail(OWNER_EMAIL, '[NEWS360 TEST – NOT POSTED] ' + label + ' ' + kindLabel + ' – ' + r.headline_ta,
      emailBody_(r, b, label, kindLabel, time, true));
    return { ok: true };
  }

  if (b.kind === 'reel') {
    var prev = r.reel_link ? r.reel_link + '\n' : '';
    sh.getRange(b.row, C.reel_link).setValue(prev + label + ': ' + b.permalink);
  } else {
    sh.getRange(b.row, PAGE_COL[b.page]).setValue(b.permalink);
    r[b.page + '_link'] = b.permalink;
    var left = targets_(r.post_to).filter(function (p) { return !r[p + '_link']; });
    sh.getRange(b.row, C.post_status).setValue(left.length ? 'Partly posted' : 'Posted');
  }
  sh.getRange(b.row, C.posted_at).setValue("'" + time);
  appendNote_(sh, b.row, r.notes, time + ' ' + kindLabel + ' posted to ' + label);

  // Google Doc: add a "Posted" section
  if (r.doc) {
    try {
      var body = DocumentApp.openByUrl(r.doc).getBody();
      body.appendParagraph('Posted to Instagram – ' + label + ' (' + kindLabel + ')').setHeading(DocumentApp.ParagraphHeading.HEADING2);
      body.appendListItem('Posted at: ' + time + ' IST');
      body.appendListItem('Instagram link: ' + b.permalink);
      if (b.kind === 'carousel') body.appendListItem('Slides: ' + b.slides);
      if (b.voice) body.appendListItem('Voice: ' + b.voice);
      body.appendListItem('Hashtags: ' + hashtags_(b.caption));
      body.appendParagraph('Caption used:').setBold(true);
      body.appendParagraph(b.caption).setBold(false);
    } catch (err) {
      appendNote_(sh, b.row, sh.getRange(b.row, C.notes).getValue(), 'Doc update failed: ' + err);
    }
  }
  GmailApp.sendEmail(OWNER_EMAIL, '[NEWS360 POSTED] ' + label + ' ' + kindLabel + ' – ' + r.headline_ta,
    emailBody_(r, b, label, kindLabel, time, false));
  props_().deleteProperty('ERR_' + b.row + '_' + b.page + '_' + b.kind);
  return { ok: true };
}

function emailBody_(r, b, label, kindLabel, time, test) {
  return [
    test ? 'TEST RUN – nothing was posted to Instagram.' : 'Posted to Instagram.',
    '',
    'Page: ' + label,
    'Type: ' + kindLabel + (b.kind === 'carousel' ? ' (' + b.slides + ' slides)' : ''),
    'Time: ' + time + ' IST',
    'Instagram link: ' + (b.permalink || '(test – not posted)'),
    b.voice ? 'Voice: ' + b.voice : '',
    '',
    'Story ID: ' + r.story_id,
    'Headline: ' + r.headline_ta,
    'English: ' + r.headline_en,
    'Category: ' + r.category + ' | Location: ' + r.location + ' | Importance: ' + r.importance,
    'Verification: ' + r.verification,
    '',
    'CAPTION USED:',
    b.caption,
    '',
    'HASHTAGS: ' + hashtags_(b.caption),
    '',
    'Images / video used: ' + (b.media_urls || []).join('\n'),
    '',
    'Sources (not shown on Instagram): ' + r.source + (r.other_sources ? '\n' + r.other_sources : ''),
    'Google Doc: ' + r.doc,
    'Sheet: ' + SHEET_LINK,
    'Notion: ' + r.notion
  ].filter(function (x) { return x !== null; }).join('\n');
}

function appendNote_(sh, row, oldNotes, text) {
  sh.getRange(row, C.notes).setValue((oldNotes ? oldNotes + '\n' : '') + text);
}

function error_(b) {
  var sh = sheet_();
  var r = rowObj_(sh.getRange(b.row, 1, 1, 28).getValues()[0], b.row);
  var key = 'ERR_' + b.row + '_' + b.page + '_' + b.kind;
  var n = Number(props_().getProperty(key) || 0) + 1;
  props_().setProperty(key, String(n));
  appendNote_(sh, b.row, r.notes, nowIst_() + ' ERROR ' + b.kind + ' ' + b.page + ' (try ' + n + '): ' + b.error);
  if (n >= 3) {
    sh.getRange(b.row, C.review).setValue('Hold');
    GmailApp.sendEmail(OWNER_EMAIL, '[NEWS360 PROBLEM] Could not post ' + r.story_id + ' – ' + r.headline_ta,
      'Posting failed 3 times, so this story is now on Hold.\n\nPage: ' + (PAGE_LABEL[b.page] || b.page) + '\nType: ' + b.kind +
      '\nError: ' + b.error + '\n\nSheet: ' + SHEET_LINK + ' (row ' + b.row + ')\nTo try again, clear "Hold" in the Review status column.');
  }
  return { ok: true };
}

// ------------------------------------------------------------------ one-time setup
/** Run once from the editor: creates the secret key, the Voice folder and the weekly token refresh. */
function setup() {
  var p = props_();
  if (!p.getProperty('BRIDGE_KEY')) p.setProperty('BRIDGE_KEY', Utilities.getUuid().replace(/-/g, ''));
  voiceFolder_();
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'refreshTokens') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('refreshTokens').timeBased().everyWeeks(1).onWeekDay(ScriptApp.WeekDay.SUNDAY).atHour(3).create();
  Logger.log('BRIDGE_KEY = ' + p.getProperty('BRIDGE_KEY'));
  Logger.log('Voice folder: https://drive.google.com/drive/folders/' + p.getProperty('VOICE_FOLDER_ID'));
}
