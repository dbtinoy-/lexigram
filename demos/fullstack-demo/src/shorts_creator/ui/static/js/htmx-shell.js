(function(){
  var updateActive = function(){
    var hasPid = (new URLSearchParams(window.location.search).get("project_id") || '').trim();
    var candidates = [window.location.pathname];
    if (hasPid) candidates.push('/projects/' + hasPid);
    var links = Array.prototype.slice.call(document.querySelectorAll('aside a'));
    var scored = links.map(function(a){
      var m = a.getAttribute('hx-get');
      if (!m) return { a: a, score: -1 };
      var mPath = m;
      var q = m.indexOf('?');
      if (q !== -1) mPath = m.substring(0, q);
      if (!mPath || mPath === '/') return { a: a, score: -1 };
      var score = -1;
      candidates.forEach(function(cur){
        if (cur === mPath) {
          if (mPath.length + 10000 > score) score = mPath.length + 10000;
        } else if (cur.indexOf(mPath + '/') === 0 && mPath.length > score) {
          score = mPath.length;
        }
      });
      return { a: a, score: score };
    });
    var best = -1;
    scored.forEach(function(s){ if (s.score > best) best = s.score; });
    scored.forEach(function(s){
      var isActive = best >= 0 && s.score === best;
      s.a.classList.toggle('bg-gradient-to-r', isActive);
      s.a.classList.toggle('from-primary/20', isActive);
      s.a.classList.toggle('to-primary/20', isActive);
      s.a.classList.toggle('text-primary', isActive);
      s.a.classList.toggle('border-primary/40', isActive);
      s.a.classList.toggle('shadow-sm', isActive);
    });
  };
  var sidebarAside = document.querySelector('aside');
  var sidebarCollapsed = (function(){
    try { return localStorage.getItem('sidebarCollapsed') === '1'; } catch (e) { return false; }
  })();
  var applySidebar = function(){
    if (!sidebarAside) return;
    sidebarAside.classList.toggle('sidebar-collapsed', sidebarCollapsed);
  };
  window.toggleSidebar = function(){
    sidebarCollapsed = !sidebarCollapsed;
    try { localStorage.setItem('sidebarCollapsed', sidebarCollapsed ? '1' : '0'); } catch (e) {}
    applySidebar();
  };
  applySidebar();
  var resolveRunsPid = function(){
    return (new URLSearchParams(window.location.search).get("project_id")) ||
      (window.location.pathname.match(/^\/projects\/([0-9a-f-]{36})/) || [])[1] || '';
  };
  var runsPid = resolveRunsPid();
  var syncRuns = function(){
    var pid = resolveRunsPid();
    if (pid !== runsPid) {
      runsPid = pid;
      document.body.dispatchEvent(new Event('sidebarRunsChanged'));
    }
  };
  updateActive();
  document.body.addEventListener('htmx:afterOnLoad', updateActive);
  document.body.addEventListener('htmx:afterSwap', function(evt) {
    syncRuns();
    updateActive();
    var scripts = evt.detail.target.querySelectorAll('script[src]');
    for (var i = 0; i < scripts.length; i++) {
      var src = scripts[i].getAttribute('src');
      if (!src || document.querySelector('script[src="' + src + '"]')) continue;
      var tag = document.createElement('script');
      tag.src = src;
      document.head.appendChild(tag);
    }
  });
  document.body.addEventListener('htmx:configRequest', function(evt) {
    var params = new URLSearchParams(window.location.search);
    var pid = params.get('project_id');
    if (pid) evt.detail.parameters['project_id'] = pid;
  });
  var progressBar = document.getElementById('htmx-progress');
  var progressTimer = null;
  if (progressBar) {
    document.body.addEventListener('htmx:beforeRequest', function() {
      progressBar.style.width = '12%';
      progressBar.style.opacity = '1';
      clearTimeout(progressTimer);
    });
    document.body.addEventListener('htmx:afterRequest', function() {
      progressBar.style.width = '100%';
      progressTimer = setTimeout(function() { progressBar.style.width = '0'; }, 400);
    });
  }
  document.body.addEventListener('htmx:beforeRequest', function(evt) {
    var elt = evt.detail.elt;
    if (!elt || !elt.getAttribute) return;
    if (elt.getAttribute('hx-target') !== '#main-content') return;
    var form = document.getElementById('project-profile-form');
    if (form && form.getAttribute('data-dirty') === 'true') {
      if (!window.confirm('You have unsaved profile changes. Leave this page?')) {
        evt.preventDefault();
      }
    }
  });
  var errorToasts = {};
  document.body.addEventListener('htmx:responseError', function(evt) {
    var xhr = evt.detail.xhr || {};
    var elt = evt.detail.elt || {};
    var key = evt.detail.requestId || (elt.id || elt.getAttribute && elt.getAttribute('hx-post')) || 'req';
    if (errorToasts[key]) return;
    errorToasts[key] = true;
    window.showToast('Request failed (' + (xhr.status || 'error') + ')', 'error');
  });
  document.body.addEventListener('htmx:sendError', function() {
    window.showToast('Network error — request could not be sent', 'error');
  });
  document.body.addEventListener('htmx:timeoutError', function() {
    window.showToast('Request timed out', 'error');
  });
  document.body.addEventListener('click', function(evt) {
    var btn = evt.target.closest ? evt.target.closest('[data-override-toggle]') : null;
    if (!btn) return;
    evt.preventDefault();
    var url = btn.getAttribute('data-reset-url');
    var key = btn.getAttribute('data-key');
    if (!url || !key) return;
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'key=' + encodeURIComponent(key)
    }).then(function(resp) {
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      return resp.text();
    }).then(function() {
      window.location.reload();
    }).catch(function() {
      if (window.showToast) window.showToast('Reset failed', 'error');
    });
  });
})();
