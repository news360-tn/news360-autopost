// ------------------------------------------------------------------ comment replies (owner 11 Nov) - NOTHING is posted without the owner
// The GitHub job poster/comments.py sends new Instagram comments with 3 reply options (action commentNew). They are kept in the private
// "Comments" tab and e-mailed to the owner, one e-mail per page per run. Each option in the e-mail is a link to a confirmation page
// (the owner can edit the text there); only the button on that page posts the reply. A link works once and expires after 48 hours.
// Comment text is never stored in the public GitHub repository or its logs.

var COMMENTS_TAB = 'Comments';
var COMMENT_COLS = ['received_ist', 'page', 'comment_id', 'media_id', 'permalink', 'post_title', 'user', 'text', 'kind',
                    'opt1', 'opt2', 'opt3', 'secret', 'status', 'reply', 'reply_id', 'done_ist', 'received_ms'];
var COMMENT_HOURS = 48;
var IG_REPLY_HOST = 'https://graph.instagram.com/v23.0/';

function commentsSheet_() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sh = ss.getSheetByName(COMMENTS_TAB);
  if (!sh) {
    sh = ss.insertSheet(COMMENTS_TAB);
    sh.appendRow(COMMENT_COLS);
    sh.setFrozenRows(1);
  }
  return sh;
}

function commentRows_() {
  var sh = commentsSheet_();
  var n = sh.getLastRow();
  if (n < 2) return [];
  var vals = sh.getRange(2, 1, n - 1, COMMENT_COLS.length).getValues();
  return vals.map(function (v, i) {
    var o = { row: i + 2 };
    COMMENT_COLS.forEach(function (c, k) { o[c] = v[k]; });
    return o;
  });
}

// GET action=commentsSeen -> the comment ids already handled (the job never sends a comment twice)
function commentsSeen_() {
  return commentRows_().map(function (r) { return String(r.comment_id); });
}

// POST action=commentNew {page, items:[{comment_id, media_id, permalink, post_title, user, text, kind, options:[..]}]}
function commentNew_(b) {
  var sh = commentsSheet_();
  var seen = {};
  commentsSeen_().forEach(function (id) { seen[id] = true; });
  var fresh = [];
  (b.items || []).forEach(function (it) {
    if (!it.comment_id || seen[String(it.comment_id)]) return;
    var o = it.options || [];
    var secret = Utilities.getUuid().replace(/-/g, '');
    sh.appendRow([nowIst_(), b.page, String(it.comment_id), String(it.media_id || ''), it.permalink || '', it.post_title || '',
                  it.user || '', it.text || '', it.kind || '', o[0] || '', o[1] || '', o[2] || '', secret, 'waiting', '', '', '', Date.now()]);
    fresh.push({ it: it, secret: secret, opts: o });
  });
  if (fresh.length) commentMail_(b.page, fresh);
  return { ok: true, added: fresh.length };
}

function commentLink_(secret, choice) {
  return ScriptApp.getService().getUrl() + '?c=' + secret + '&o=' + choice;
}

function esc_(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function commentMail_(page, fresh) {
  var label = (typeof PAGE_LABEL !== 'undefined' && PAGE_LABEL[page]) || page;
  var html = '<div style="font-family:Arial,sans-serif;font-size:15px">' +
    '<p><b>' + fresh.length + ' new comment(s) on ' + esc_(label) + '.</b> Choose a reply - you can edit it before it is posted. ' +
    'Nothing is posted until you press "Post this reply" on the next page. Links expire after ' + COMMENT_HOURS + ' hours.</p>';
  fresh.forEach(function (f) {
    var it = f.it;
    html += '<div style="border:1px solid #ddd;border-radius:10px;padding:12px;margin:14px 0">' +
      '<div style="color:#666">Post: <a href="' + esc_(it.permalink) + '">' + esc_(it.post_title) + '</a></div>' +
      '<div style="margin:8px 0"><b>@' + esc_(it.user) + '</b>: ' + esc_(it.text) + '</div>' +
      (it.kind ? '<div style="color:#a00;font-size:13px">' + esc_(it.kind) + '</div>' : '');
    f.opts.forEach(function (o, k) {
      if (!o) return;
      html += '<div style="margin:6px 0"><a href="' + commentLink_(f.secret, k + 1) + '" style="display:inline-block;background:#1a73e8;color:#fff;' +
        'padding:8px 12px;border-radius:6px;text-decoration:none">Reply ' + (k + 1) + '</a> ' + esc_(o) + '</div>';
    });
    html += '<div style="margin-top:8px"><a href="' + commentLink_(f.secret, 'own') + '">Write my own reply</a> &nbsp;|&nbsp; ' +
      '<a href="' + commentLink_(f.secret, 'skip') + '">Skip</a> &nbsp;|&nbsp; ' +
      '<a href="' + commentLink_(f.secret, 'hide') + '">Hide this comment</a></div></div>';
  });
  html += '</div>';
  GmailApp.sendEmail(OWNER_EMAIL, '[' + label + ' COMMENTS] ' + fresh.length + ' new - choose replies',
    'Open this e-mail in HTML view to choose the replies.', { htmlBody: html });
}

function commentFind_(secret) {
  if (!secret) return null;
  var rows = commentRows_();
  for (var i = 0; i < rows.length; i++) if (String(rows[i].secret) === String(secret)) return rows[i];
  return null;
}

function commentOpen_(r) {
  if (!r) return 'This link is not valid.';
  if (r.status !== 'waiting') return 'Already handled: ' + r.status + (r.reply ? ' - "' + r.reply + '"' : '') + '.';
  var t = Number(r.received_ms) || 0;
  if (!t || (Date.now() - t) > COMMENT_HOURS * 3600 * 1000) return 'This link has expired (older than ' + COMMENT_HOURS + ' hours).';
  return '';
}

function htmlPage_(body) {
  return HtmlService.createHtmlOutput('<div style="font-family:Arial,sans-serif;font-size:17px;max-width:640px;margin:24px auto;padding:0 16px">' +
    body + '</div>').setTitle('Comment reply').addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

// GET ?c=<secret>&o=1|2|3|own|skip|hide -> a confirmation page only (e-mail link scanners can open it safely; nothing is posted here)
function commentPage_(e) {
  var r = commentFind_(e.parameter.c);
  var bad = commentOpen_(r);
  if (bad) return htmlPage_('<p>' + esc_(bad) + '</p>');
  var o = String(e.parameter.o || '');
  var head = '<p style="color:#666">@' + esc_(r.user) + ' wrote:</p><p><b>' + esc_(r.text) + '</b></p>';
  var form = function (what, inner, button) {
    return '<form method="post" action="' + ScriptApp.getService().getUrl() + '" target="_top">' +
      '<input type="hidden" name="c" value="' + esc_(r.secret) + '"><input type="hidden" name="what" value="' + what + '">' + inner +
      '<p><button type="submit" style="font-size:17px;padding:10px 18px;background:#1a73e8;color:#fff;border:0;border-radius:6px">' + button + '</button></p></form>';
  };
  if (o === 'skip') return htmlPage_(head + form('skip', '', 'Skip this comment (no reply)'));
  if (o === 'hide') return htmlPage_(head + form('hide', '<p>The comment will be hidden from other viewers on Instagram.</p>', 'Hide this comment'));
  var text = { '1': r.opt1, '2': r.opt2, '3': r.opt3 }[o] || '';
  return htmlPage_(head + form('reply', '<p>Your reply (edit if needed):</p><textarea name="reply" rows="5" style="width:100%;font-size:17px">' +
    esc_(text) + '</textarea>', 'Post this reply'));
}

// POST from the confirmation page (form fields c, what, reply)
function commentSubmit_(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var r = commentFind_(e.parameter.c);
    var bad = commentOpen_(r);
    if (bad) return htmlPage_('<p>' + esc_(bad) + '</p>');
    var sh = commentsSheet_();
    var col = function (name) { return COMMENT_COLS.indexOf(name) + 1; };
    var what = String(e.parameter.what || '');
    if (what === 'skip') {
      sh.getRange(r.row, col('status')).setValue('skipped');
      sh.getRange(r.row, col('done_ist')).setValue(nowIst_());
      return htmlPage_('<p>Skipped - no reply posted.</p>');
    }
    var tok = token_(r.page);
    if (what === 'hide') {
      var h = UrlFetchApp.fetch(IG_REPLY_HOST + r.comment_id, { method: 'post', muteHttpExceptions: true,
        payload: { hide: 'true', access_token: tok } });
      if (h.getResponseCode() !== 200) return htmlPage_('<p>Instagram did not hide it: ' + esc_(h.getContentText().slice(0, 300)) + '</p>');
      sh.getRange(r.row, col('status')).setValue('hidden');
      sh.getRange(r.row, col('done_ist')).setValue(nowIst_());
      return htmlPage_('<p>Comment hidden ✅</p>');
    }
    var msg = String(e.parameter.reply || '').trim();
    if (!msg) return htmlPage_('<p>The reply is empty - nothing posted.</p>');
    var res = UrlFetchApp.fetch(IG_REPLY_HOST + r.comment_id + '/replies', { method: 'post', muteHttpExceptions: true,
      payload: { message: msg.slice(0, 2200), access_token: tok } });
    if (res.getResponseCode() !== 200) return htmlPage_('<p>Instagram did not accept the reply: ' + esc_(res.getContentText().slice(0, 300)) +
      '</p><p>Nothing was posted. You can go back and try again.</p>');
    var id = (JSON.parse(res.getContentText()) || {}).id || '';
    sh.getRange(r.row, col('status')).setValue('replied');
    sh.getRange(r.row, col('reply')).setValue(msg);
    sh.getRange(r.row, col('reply_id')).setValue(id);
    sh.getRange(r.row, col('done_ist')).setValue(nowIst_());
    return htmlPage_('<p>Reply posted ✅</p><p>' + esc_(msg) + '</p><p><a href="' + esc_(r.permalink) + '">Open the post</a></p>');
  } finally {
    lock.releaseLock();
  }
}
