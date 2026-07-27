window.showToast = function(message, type) {
  var c = document.getElementById('toast-container');
  if (!c) { c = document.createElement('div'); c.id = 'toast-container'; c.className = 'toast-container'; document.body.appendChild(c); }
  var t = document.createElement('div'); t.className = 'toast toast-' + type;
  t.innerHTML = message;
  c.appendChild(t);
  setTimeout(function() { t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; setTimeout(function() { t.remove(); }, 300); }, 3500);
};
document.body.addEventListener('showToast', function(e) { window.showToast(e.detail.message, e.detail.type || 'info'); });