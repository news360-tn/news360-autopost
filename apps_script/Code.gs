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
  slides_spec: 22, post_status: 23, posted_at: 24, rasipuram_link: 25, namakkal_link: 26, reel_link: 27, notes: 28,
  batch: 29, prompts: 30, images: 31
};
var NCOLS = 31;
var CLOUD_NAME = 'bgk9wm1u';
var UPLOAD_PRESET = 'news360';
var MIN_IMAGES = 3;
var EXPIRE_HOURS = 12;
var COLLAB_USERNAME = 'rasipuram.360';
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
/** Only நாமக்கல் 360 posts. Rasipuram stories add இராசிபுரம் 360 as a collaborator instead of a second post. */
function targets_(postTo) { return ['namakkal']; }
function queue_() {
  var sh = sheet_();
  var last = sh.getLastRow();
  if (last < 2) return [];
  var data = sh.getRange(2, 1, last - 1, NCOLS).getValues();
  var out = [];
  for (var i = 0; i < data.length; i++) {
    var r = rowObj_(data[i], i + 2);
    var st = r.post_status.toLowerCase();
    if (!r.story_id || !r.slides_spec || !r.images) continue;
    if (st !== 'queued' && st !== 'partly posted' && st !== 'posted') continue;
    if (r.review.toLowerCase() === 'hold') continue;
    var pagesLeft = targets_(r.post_to).filter(function (p) { return !r[p + '_link']; }).length;
    var reelLeft = !r.reel_link;
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
  var vals = sh.getRange(b.row, 1, 1, NCOLS).getValues()[0];
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
    if (r.namakkal_link) sh.getRange(b.row, C.post_status).setValue('Posted');
  } else {
    sh.getRange(b.row, PAGE_COL[b.page]).setValue(b.permalink);
    r[b.page + '_link'] = b.permalink;
    sh.getRange(b.row, C.post_status).setValue(r.reel_link ? 'Posted' : 'Partly posted');
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
    b.checks ? 'Checks passed before posting: ' + b.checks : '',
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
    b.collab ? 'Collaboration invite sent to @' + COLLAB_USERNAME + ' – open the இராசிபுரம் 360 app → notifications and tap Accept so the post also shows on that page.' : '',
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
  var r = rowObj_(sh.getRange(b.row, 1, 1, NCOLS).getValues()[0], b.row);
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

// ------------------------------------------------------------------ reading your image reply
/**
 * Runs every 5 minutes. Looks for your reply to a "[NEWS360 IMAGES NEEDED]" email, takes the attached images
 * (a zip, or the images themselves), uploads them to Cloudinary, saves the links in the Sheet and queues the story.
 * Skip a story by writing  SKIP RN-26  in your reply (e.g. when you already posted it yourself).
 */
function processReplies() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) return;
  try {
    expireOld_();
    var p = props_();
    var done = JSON.parse(p.getProperty('DONE_MSGS') || '[]');
    var allowed = allowedSenders_();
    var threads = GmailApp.search('subject:"NEWS360 IMAGES NEEDED" newer_than:5d', 0, 20);
    threads.forEach(function (th) {
      var m = th.getFirstMessageSubject().match(/B\d{8}-\d{4}/);
      if (!m) return;
      th.getMessages().forEach(function (msg) {
        var id = msg.getId();
        if (done.indexOf(id) >= 0) return;
        var from = String(msg.getFrom()).replace(/^.*<|>.*$/g, '').trim().toLowerCase();
        if (allowed.indexOf(from) < 0) return;
        done.push(id);
        p.setProperty('DONE_MSGS', JSON.stringify(done.slice(-200)));
        try { handleReply_(msg, m[0]); } catch (err) {
          GmailApp.sendEmail(OWNER_EMAIL, '[NEWS360 PROBLEM] Could not read your image reply', String(err) + '\n\nBatch ' + m[0]);
        }
      });
    });
  } finally {
    lock.releaseLock();
  }
}

function allowedSenders_() {
  var extra = String(props_().getProperty('ALLOWED_SENDERS') || '').split(',');
  return [OWNER_EMAIL.toLowerCase()].concat(extra.map(function (x) { return x.trim().toLowerCase(); }).filter(String));
}

function imageBlobs_(msg) {
  var out = [];
  msg.getAttachments({ includeInlineImages: false, includeAttachments: true }).forEach(function (a) {
    var n = String(a.getName()).toLowerCase();
    var blobs = (n.slice(-4) === '.zip' || a.getContentType().indexOf('zip') >= 0) ? Utilities.unzip(a) : [a];
    blobs.forEach(function (b) {
      var bn = String(b.getName());
      if (/(^|\/)\.|__MACOSX/.test(bn)) return;
      if (/\.(png|jpe?g|webp)$/i.test(bn)) out.push(b);
    });
  });
  return out;
}

function naturalKey_(name) {
  return String(name).replace(/\d+/g, function (d) { return ('00000000' + d).slice(-8); }).toLowerCase();
}

function handleReply_(msg, batchId) {
  var sh = sheet_();
  var last = sh.getLastRow();
  if (last < 2) return;
  var data = sh.getRange(2, 1, last - 1, NCOLS).getValues();
  var rows = [];
  for (var i = 0; i < data.length; i++) {
    var r = rowObj_(data[i], i + 2);
    if (r.batch === batchId && r.post_status === 'Awaiting images' && r.review.toLowerCase() !== 'hold') rows.push(r);
  }
  var report = [];

  // SKIP lines (only in what you typed, not in the quoted original)
  var body = String(msg.getPlainBody()).replace(/\r/g, '');
  // cut everything from the quoted original ("On <date> ... wrote:" which may wrap over two lines, "> " lines, "Original Message")
  var cut = body.search(/(^|\n)[ \t]*On [^\n]*(\n[^\n]*)?wrote:|(^|\n)[ \t]*>|(^|\n)[ \t]*-{2,}[ \t]*Original|(^|\n)[ \t]*From:/i);
  var typed = cut >= 0 ? body.slice(0, cut) : body;
  var skipped = {};
  // only a line that STARTS with SKIP counts (so example text can never trigger it)
  (typed.match(/^[ \t]*SKIP[ \t]+RN-?\d+/gmi) || []).forEach(function (x) {
    skipped['RN-' + x.match(/\d+/)[0]] = true;
  });
  rows = rows.filter(function (r) {
    if (skipped[r.story_id]) {
      sh.getRange(r.row, C.review).setValue('Hold');
      sh.getRange(r.row, C.post_status).setValue('Skipped (posted manually)');
      report.push(r.story_id + ': skipped as you asked');
      return false;
    }
    return true;
  });

  var blobs = imageBlobs_(msg);
  if (blobs.length && rows.length) {
    var byStory = {};
    var unnamed = [];
    blobs.forEach(function (b) {
      var nm = String(b.getName());
      var sm = nm.match(/RN-?(\d+)/i);
      if (sm) {
        var key = 'RN-' + sm[1];
        (byStory[key] = byStory[key] || []).push(b);
      } else unnamed.push(b);
    });
    unnamed.sort(function (a, b) { return naturalKey_(a.getName()) < naturalKey_(b.getName()) ? -1 : 1; });
    rows.forEach(function (r) {
      var need = promptCount_(r);
      var mine = (byStory[r.story_id] || []).sort(function (a, b) { return naturalKey_(a.getName()) < naturalKey_(b.getName()) ? -1 : 1; });
      while (mine.length < need && unnamed.length) mine.push(unnamed.shift());
      mine = mine.slice(0, 10);
      if (mine.length < Math.min(MIN_IMAGES, need)) {
        if (mine.length) report.push(r.story_id + ': only ' + mine.length + ' image(s) found, need ' + need + ' – please reply again with all ' + need + ' images');
        else report.push(r.story_id + ': no images found yet');
        return;
      }
      var urls = mine.map(function (b) { return uploadImage_(b, r.story_id); });
      sh.getRange(r.row, C.images).setValue(JSON.stringify(urls));
      sh.getRange(r.row, C.post_status).setValue('Queued');
      appendNote_(sh, r.row, r.notes, nowIst_() + ' ' + urls.length + ' images received (batch ' + batchId + ')');
      report.push(r.story_id + ': ' + urls.length + ' images received – carousel and reel will be made and posted within about 20-40 minutes');
    });
  } else if (!report.length && rows.length) {
    return; // e.g. the original email itself: nothing to do
  }
  if (report.length) {
    GmailApp.sendEmail(OWNER_EMAIL, '[NEWS360 IMAGES RECEIVED] ' + batchId,
      report.join('\n') + '\n\nSheet: ' + SHEET_LINK);
  }
}

function promptCount_(r) {
  var n = String(r.prompts || '').split(/\n-{3,}\n/).filter(function (x) { return x.trim(); }).length;
  return n || 5;
}

function uploadImage_(blob, story) {
  var res = UrlFetchApp.fetch('https://api.cloudinary.com/v1_1/' + CLOUD_NAME + '/image/upload', {
    method: 'post', muteHttpExceptions: true,
    payload: { file: blob, upload_preset: UPLOAD_PRESET, folder: 'news360/src/' + story }
  });
  var d = JSON.parse(res.getContentText());
  if (!d.secure_url) throw new Error('Image upload failed for ' + story + ': ' + res.getContentText().slice(0, 300));
  return d.secure_url;
}

/** Stories still waiting for images after EXPIRE_HOURS are closed, so old news is never posted. */
function expireOld_() {
  var sh = sheet_();
  var last = sh.getLastRow();
  if (last < 2) return;
  var data = sh.getRange(2, 1, last - 1, NCOLS).getValues();
  for (var i = 0; i < data.length; i++) {
    var r = rowObj_(data[i], i + 2);
    if (r.post_status !== 'Awaiting images') continue;
    var t = parseIst_(r.researched);
    if (t && (Date.now() - t.getTime()) / 3600000 > EXPIRE_HOURS) {
      sh.getRange(r.row, C.post_status).setValue('Expired - no images');
      appendNote_(sh, r.row, r.notes, nowIst_() + ' expired: no images within ' + EXPIRE_HOURS + ' hours');
    }
  }
}
function parseIst_(txt) {
  var m = String(txt).replace(/^'/, '').match(/(\d{1,2}) (\w{3}) (\d{4}),? (\d{1,2}):(\d{2})/);
  if (!m) return null;
  var mon = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 }[m[2]];
  if (mon === undefined) return null;
  return new Date(Date.UTC(+m[3], mon, +m[1], +m[4], +m[5]) - 5.5 * 3600000);
}

// ------------------------------------------------------------------ one-time setup
/** Run once from the editor (and again after every update): secret key, Voice folder, triggers. Asks for Gmail permission. */
function setup() {
  var p = props_();
  if (!p.getProperty('BRIDGE_KEY')) p.setProperty('BRIDGE_KEY', Utilities.getUuid().replace(/-/g, ''));
  voiceFolder_();
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var h = t.getHandlerFunction();
    if (h === 'refreshTokens' || h === 'processReplies') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('refreshTokens').timeBased().everyWeeks(1).onWeekDay(ScriptApp.WeekDay.SUNDAY).atHour(3).create();
  ScriptApp.newTrigger('processReplies').timeBased().everyMinutes(5).create();
  GmailApp.getInboxThreads(0, 1); // makes Google ask for Gmail permission now
  Logger.log('BRIDGE_KEY is saved in Script properties (not shown here).');
  Logger.log('Voice folder: https://drive.google.com/drive/folders/' + p.getProperty('VOICE_FOLDER_ID'));
}
