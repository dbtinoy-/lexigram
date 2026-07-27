window.__lp = window.__lp || { active: {}, count: 0 };
window.__lp.loadHistory = function() {
  var since = localStorage.getItem('lp_since');
  var url = '/api/logs';
  if (since) url += '?since=' + encodeURIComponent(since);
  fetch(url).then(function(r) { return r.text(); }).then(function(html) {
    var el = document.getElementById('log-entries');
    if (el && html) {
      el.innerHTML = html + (el.innerHTML ? '<div class="lp-separator"></div>' : '') + el.innerHTML;
      var count = el.querySelectorAll('.lp-entry').length;
      window.__lp.count = count;
      var badge = document.getElementById('lp-badge');
      if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'inline' : 'none'; }
    }
  }).catch(function(){});
};
window.__lp.clearLog = function() {
  var el = document.getElementById('log-entries');
  if (el) el.innerHTML = '';
  window.__lp.count = 0;
  var badge = document.getElementById('lp-badge');
  if (badge) { badge.textContent = '0'; badge.style.display = 'none'; }
  localStorage.removeItem('lp_since');
};
window.__lp.addEntry = function(opId, type, message) {
  var el = document.getElementById('log-entries');
  if (!el) return;
  var entry = document.createElement('div');
  entry.className = 'lp-entry lp-' + type;
  var t = new Date().toLocaleTimeString();
  entry.innerHTML = '<span class="lp-time">' + t + '</span>'
    + '<span class="lp-op">' + opId + '</span>'
    + '<span class="lp-msg">' + message + '</span>';
  el.appendChild(entry);
  el.scrollTop = el.scrollHeight;
  window.__lp.count++;
  var badge = document.getElementById('lp-badge');
  if (badge) { badge.textContent = window.__lp.count; badge.style.display = 'inline'; }
  localStorage.setItem('lp_since', new Date().toISOString());
};
window.__lp.toggle = function() {
  var p = document.getElementById('log-panel');
  p.classList.toggle('open');
};
window.__lp.connect = function(opId, onDone) {
  if (window.__lp.active[opId]) return;
  var es = new EventSource('/api/progress/' + encodeURIComponent(opId));
  window.__lp.active[opId] = es;
  var settled = false;
  function finish(err, evt) {
    if (settled) return;
    settled = true;
    if (es.readyState !== EventSource.CLOSED) { try { es.close(); } catch(ex) {} }
    delete window.__lp.active[opId];
    if (onDone) onDone(err || null, evt || null);
  }
  window.__lp.addEntry(opId, 'connected', 'Connected');
  es.addEventListener('connected', function(e) {
    window.__lp.addEntry(opId, 'connected', 'Connected to stream');
  });
  es.addEventListener('progress', function(e) {
    try { var d = JSON.parse(e.data); window.__lp.addEntry(opId, 'progress', d.message || d.stage || 'Working...'); } catch(ex) {}
  });
  es.addEventListener('complete', function(e) {
    try { var d = JSON.parse(e.data); window.__lp.addEntry(opId, 'success', d.message || 'Complete'); } catch(ex) { window.__lp.addEntry(opId, 'success', 'Complete'); }
    finish(null, e);
  });
  es.addEventListener('failed', function(e) {
    var d = null;
    try { d = JSON.parse(e.data); window.__lp.addEntry(opId, 'error', d.error || 'Failed'); } catch(ex) { window.__lp.addEntry(opId, 'error', 'Failed'); }
    finish(new Error(d && d.error || 'Failed'), e);
  });
  es.onerror = function() {
    window.__lp.addEntry(opId, 'error', 'Connection lost');
    finish(new Error('Connection lost'), null);
  };
};
window.__lp.disconnectAll = function() {
  for (var k in window.__lp.active) { window.__lp.active[k].close(); }
  window.__lp.active = {};
};
window.__lp.loadHistory();