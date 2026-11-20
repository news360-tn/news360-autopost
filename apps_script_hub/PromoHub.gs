/**
 * 360 News - PROMO HUB (one Apps Script for ALL pages; owner 20 Nov).
 *
 *  1. Promotion ads: one Google Form for every page -> a sample reel is e-mailed to the owner -> the owner replies
 *     APPROVED, or REJECTED + the changes -> a new sample until approved -> only then the ad goes on the news reels of the
 *     chosen pages, between the start and end date, at most N reels a day per page. The ad is the big bottom box during the
 *     news only; the page's own FOLLOW end card never changes.
 *  2. YouTube details: twice a day every page sends its summary here and the owner gets ONE e-mail per page with the
 *     reels to upload to that page's YouTube channel (title, description, tags, time, download link).
 *
 * ONE-TIME SETUP (the steps are in the SETUP guide):
 *   a) script.google.com > New project > paste this file > Save > run setup() > allow the permissions.
 *      The Execution log prints the FORM LINK, the EDIT FORM link, the SHEET link and the KEY.
 *   b) Deploy > New deployment > type "Web app" > Execute as: Me > Who has access: Anyone > Deploy > copy the Web app URL.
 *   c) Every page repo on GitHub > Settings > Secrets and variables > Actions > New secret:
 *        PROMO_URL = the Web app URL      PROMO_KEY = the KEY from the log
 *   d) Open the EDIT FORM link and add the upload question (Google does not let a script add it):
 *        + > File upload > title "Logo / picture" > allow only Image > 1 file > 10 MB.
 *
 * The "Promos" sheet can also be edited by hand: Status "stopped" stops an ad at once; "approved" starts it.
 */

var PAGES = {
  'நாமக்கல் 360': 'namakkal', 'இராசிபுரம் 360': 'rasipuram', 'கோயம்புத்தூர் 360': 'coimbatore', 'சேலம் 360': 'salem',
  'ஈரோடு 360': 'erode', 'கரூர் 360': 'karur', 'திருப்பூர் 360': 'tirupur', 'திருச்சி 360': 'trichy'
};
var ALL = 'All pages / அனைத்து பக்கங்களும்';
var COLS = ['id', 'created', 'pages', 'brand', 'title', 'message', 'start', 'end', 'per_day', 'notes', 'file_ids', 'status',
            'owner_points', 'sample_url', 'sample_thread', 'sample_msgs', 'approved_at', 'updated'];
var Q = { pages: 'Page(s) / பக்கம்', brand: 'Sponsor / brand name (நிறுவனத்தின் பெயர்)', title: 'Ad title - shown big (max 40 letters)',
          message: 'Ad message - 2 short lines (max 80 letters)', start: 'Start date (ad starts on this day)',
          end: 'End date (last day of the ad)', per_day: 'How many news reels per day, per page', notes: 'Notes (optional)' };

function props_() { return PropertiesService.getScriptProperties(); }
function owner_() { return Session.getEffectiveUser().getEmail(); }
function now_() { return Utilities.formatDate(new Date(), 'Asia/Kolkata', 'yyyy-MM-dd HH:mm'); }
function json_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

// ------------------------------------------------------------------ setup (run once)
function setup() {
  var p = props_();
  if (!p.getProperty('KEY')) p.setProperty('KEY', Utilities.getUuid().replace(/-/g, ''));
  var form = p.getProperty('FORM_ID') ? FormApp.openById(p.getProperty('FORM_ID')) : createForm_();
  p.setProperty('FORM_ID', form.getId());
  var ss;
  if (p.getProperty('SHEET_ID')) {
    ss = SpreadsheetApp.openById(p.getProperty('SHEET_ID'));
  } else {
    ss = SpreadsheetApp.create('360 News - Promotions');
    form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
    p.setProperty('SHEET_ID', ss.getId());
  }
  var sh = ss.getSheetByName('Promos') || ss.insertSheet('Promos');
  if (sh.getLastRow() === 0) sh.appendRow(COLS);
  var used = ss.getSheetByName('Used') || ss.insertSheet('Used');
  if (used.getLastRow() === 0) used.appendRow(['id', 'page', 'date', 'story', 'time']);
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('onPromoSubmit').forForm(form).onFormSubmit().create();
  ScriptApp.newTrigger('checkReplies').timeBased().everyMinutes(10).create();
  Logger.log('FORM LINK (fill / share this): ' + form.getPublishedUrl());
  Logger.log('EDIT FORM (add the upload question here): ' + form.getEditUrl());
  Logger.log('SHEET (all requests and their status): ' + ss.getUrl());
  Logger.log('KEY (GitHub secret PROMO_KEY): ' + p.getProperty('KEY'));
  Logger.log('Next: Deploy > New deployment > Web app > Execute as Me > Anyone > copy the URL into GitHub secret PROMO_URL');
}

function createForm_() {
  var form = FormApp.create('360 News - Promotion / விளம்பரம் request');
  form.setDescription('One form for every page. The ad shows at the bottom of the news reels, during the news only, on the pages ' +
                      'and dates below - only after the owner approves the sample sent by e-mail.');
  form.addCheckboxItem().setTitle(Q.pages).setChoiceValues([ALL].concat(Object.keys(PAGES))).setRequired(true);
  form.addTextItem().setTitle(Q.brand).setRequired(true);
  form.addTextItem().setTitle(Q.title)
      .setValidation(FormApp.createTextValidation().requireTextLengthLessThanOrEqualTo(40).build()).setRequired(true);
  form.addParagraphTextItem().setTitle(Q.message)
      .setValidation(FormApp.createParagraphTextValidation().requireTextLengthLessThanOrEqualTo(80).build()).setRequired(true);
  form.addDateItem().setTitle(Q.start).setRequired(true);
  form.addDateItem().setTitle(Q.end).setRequired(true);
  form.addMultipleChoiceItem().setTitle(Q.per_day).setChoiceValues(['All news reels', '1', '2', '3', '5']).setRequired(true);
  form.addParagraphTextItem().setTitle(Q.notes);
  return form;
}

// ------------------------------------------------------------------ the sheet
function sheet_(name) { return SpreadsheetApp.openById(props_().getProperty('SHEET_ID')).getSheetByName(name || 'Promos'); }

function rows_() {
  var sh = sheet_(), last = sh.getLastRow();
  if (last < 2) return [];
  return sh.getRange(2, 1, last - 1, COLS.length).getValues().map(function (v, i) {
    var o = { row: i + 2 };
    COLS.forEach(function (c, j) { o[c] = v[j] instanceof Date ? Utilities.formatDate(v[j], 'Asia/Kolkata', 'yyyy-MM-dd') : String(v[j]); });
    return o;
  });
}

function set_(row, fields) {
  var sh = sheet_();
  fields.updated = now_();
  Object.keys(fields).forEach(function (k) {
    var c = COLS.indexOf(k);
    if (c >= 0) sh.getRange(row, c + 1).setValue(fields[k]);
  });
}

// ------------------------------------------------------------------ a new request from the form
function onPromoSubmit(e) {
  var a = {}, files = [];
  e.response.getItemResponses().forEach(function (ir) {
    var t = ir.getItem().getTitle(), r = ir.getResponse();
    if (ir.getItem().getType() === FormApp.ItemType.FILE_UPLOAD) { files = files.concat(r || []); return; }
    a[t] = r;
  });
  var chosen = [].concat(a[Q.pages] || []);
  var pages = chosen.indexOf(ALL) >= 0 ? Object.keys(PAGES).map(function (k) { return PAGES[k]; })
                                       : chosen.map(function (k) { return PAGES[k]; }).filter(String);
  var n = Math.max(0, sheet_().getLastRow() - 1) + 1;
  var per = String(a[Q.per_day] || 'All news reels');
  sheet_().appendRow(['PR-' + n, now_(), pages.join(','), a[Q.brand] || '', a[Q.title] || '', a[Q.message] || '',
                      a[Q.start] || '', a[Q.end] || '', /^\d+$/.test(per) ? per : 'all', a[Q.notes] || '', files.join(','),
                      'sample_needed', '', '', '', '', '', now_()]);
}

// ------------------------------------------------------------------ the owner's reply to a sample
function checkReplies() {
  rows_().forEach(function (r) {
    if (r.status !== 'sample_sent') return;
    var th = null;
    try { th = r.sample_thread ? GmailApp.getThreadById(r.sample_thread) : null; } catch (err) { th = null; }
    if (!th) {      // the thread id was not saved (Gmail was slow): find the sample e-mail by its subject
      th = GmailApp.search('subject:"[360 PROMO SAMPLE] ' + r.id + ' - " newer_than:30d', 0, 1)[0];
      if (!th) return;
      set_(r.row, { sample_thread: th.getId() });
    }
    var msgs = th.getMessages(), seen = Number(r.sample_msgs || 1);
    for (var i = seen; i < msgs.length; i++) {
      var body = String(msgs[i].getPlainBody() || '').split(/\n\s*On .{0,120}wrote:|\n>/)[0].trim();
      var first = body.split('\n')[0].trim().toUpperCase();
      if (/^(APPROVED?|OK|YES)\b/.test(first)) {
        set_(r.row, { status: 'approved', approved_at: now_(), sample_msgs: msgs.length });
        GmailApp.sendEmail(owner_(), '[360 PROMO APPROVED] ' + r.id + ' - ' + r.brand,
          'Approved. The ad runs from ' + r.start + ' to ' + r.end + ' on: ' + r.pages + ' (' +
          (r.per_day === 'all' ? 'all news reels' : r.per_day + ' news reels a day per page') + ').\n' +
          'To stop it early: in the sheet, set Status of ' + r.id + ' to "stopped".');
        return;
      }
      if (/^(REJECT|REJECTED|NO|CHANGE)/.test(first)) {
        set_(r.row, { status: 'changes', owner_points: body.replace(/^\S+\s*[:\-]?\s*/, '').slice(0, 1500), sample_msgs: msgs.length });
        return;
      }
      if (/^STOP/.test(first)) { set_(r.row, { status: 'stopped', sample_msgs: msgs.length }); return; }
    }
  });
}

// ------------------------------------------------------------------ setup from the phone (no editor needed)
// Open  <Web app URL>?setup=1  once, signed in as the owner, and allow the permissions: setup() runs and the page shows the links
// and the KEY. It shows the KEY only that first time; after that the KEY is in Project Settings > Script properties.
function setupPage_() {
  var first = !props_().getProperty('KEY');
  if (!first) return HtmlService.createHtmlOutput('<h2>360 Promo Hub is already set up.</h2>' +
      '<p>The KEY is in the Apps Script project: Project Settings &gt; Script properties.</p>');
  setup();
  var p = props_(), form = FormApp.openById(p.getProperty('FORM_ID')), ss = SpreadsheetApp.openById(p.getProperty('SHEET_ID'));
  var a = function (u, t) { return '<p><b>' + t + '</b><br><a href="' + u + '">' + u + '</a></p>'; };
  return HtmlService.createHtmlOutput('<meta name="viewport" content="width=device-width,initial-scale=1">' +
      '<div style="font-family:Arial;font-size:16px;padding:12px"><h2>360 Promo Hub - set up</h2>' +
      a(form.getPublishedUrl(), 'FORM LINK (fill / share)') + a(form.getEditUrl(), 'EDIT FORM (add the File upload question)') +
      a(ss.getUrl(), 'SHEET (requests and status)') +
      '<p><b>KEY</b> - copy it into GitHub secret <b>PROMO_KEY</b> in all 7 repos (shown only this once):</p>' +
      '<p style="font-family:monospace;font-size:18px;background:#eee;padding:10px;word-break:break-all">' + p.getProperty('KEY') + '</p></div>');
}

// ------------------------------------------------------------------ the page repos (GitHub) talk to the hub
function authorized_(e) { return e && e.parameter && e.parameter.key && e.parameter.key === props_().getProperty('KEY'); }

function doGet(e) {
  if (e && e.parameter && e.parameter.setup === '1') return setupPage_();
  if (!authorized_(e)) return json_({ ok: false, error: 'unauthorized' });
  try {
    var a = e.parameter.action;
    if (a === 'promos') return json_({ ok: true, promos: rows_(), used: used_() });
    if (a === 'file') {
      var f = DriveApp.getFileById(e.parameter.id), b = f.getBlob();
      return json_({ ok: true, name: f.getName(), mime: b.getContentType(), data: Utilities.base64Encode(b.getBytes()) });
    }
    if (a === 'ping') return json_({ ok: true, time: now_() });
    return json_({ ok: false, error: 'unknown action ' + a });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

function used_() {
  var sh = sheet_('Used'), last = sh.getLastRow(), out = {};
  if (last < 2) return out;
  var from = Math.max(2, last - 3000);
  sh.getRange(from, 1, last - from + 1, 3).getValues().forEach(function (v) {
    var d = v[2] instanceof Date ? Utilities.formatDate(v[2], 'Asia/Kolkata', 'yyyy-MM-dd') : String(v[2]);
    var k = v[0] + '|' + v[1] + '|' + d;
    out[k] = (out[k] || 0) + 1;
  });
  return out;
}

function doPost(e) {
  if (!authorized_(e)) return json_({ ok: false, error: 'unauthorized' });
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var b = JSON.parse(e.postData.contents || '{}');
    var r = b.id ? rows_().filter(function (x) { return x.id === b.id; })[0] : null;
    if (b.action === 'used') {
      sheet_('Used').appendRow([b.id, b.page, b.date, b.story || '', now_()]);
      return json_({ ok: true });
    }
    if (b.action === 'update' && r) {
      var f = {};
      ['title', 'message', 'status'].forEach(function (k) { if (b[k] !== undefined) f[k] = b[k]; });
      set_(r.row, f);
      return json_({ ok: true });
    }
    if (b.action === 'sample' && r) {
      var subject = '[360 PROMO SAMPLE] ' + r.id + ' - ' + r.brand;
      var text = 'Sample reel with your ad (' + b.page_label + ', news: ' + (b.headline || '') + '):\n' + b.video_url + '\n\n' +
        'Ad title: ' + (b.title || r.title) + '\nAd message: ' + (b.message || r.message) + '\nPages: ' + r.pages +
        '\nDates: ' + r.start + ' to ' + r.end + '\nReels a day per page: ' + r.per_day + '\n' +
        (b.not_applied ? '\nThese points could not be applied automatically: ' + b.not_applied + '\n' : '') +
        '\nREPLY to this e-mail with:\n  APPROVED  - the ad starts on the start date\n' +
        '  REJECTED  followed by your changes (e.g. "REJECTED change the title to ...")\n  STOP  - cancel this request\n';
      GmailApp.sendEmail(owner_(), subject, text);
      Utilities.sleep(3000);
      var th = GmailApp.search('subject:"' + subject + '" newer_than:1d', 0, 1)[0];
      set_(r.row, { status: 'sample_sent', sample_url: b.video_url, sample_thread: th ? th.getId() : '',
                    sample_msgs: th ? th.getMessageCount() : 1 });
      return json_({ ok: true });
    }
    if (b.action === 'digest') {
      GmailApp.sendEmail(owner_(), b.subject, b.text || '', b.html ? { htmlBody: b.html } : {});
      return json_({ ok: true });
    }
    return json_({ ok: false, error: 'unknown action or id' });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}
