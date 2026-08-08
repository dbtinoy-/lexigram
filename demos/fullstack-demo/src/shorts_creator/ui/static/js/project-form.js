var _fw_active_classes = __ACTIVE_CLASSES__;
var _fw_inactive_classes = ['bg-card/60','border-border','text-muted-foreground'];
var _fw_active_format = ['bg-gradient-to-br','from-primary','to-primary','border-primary','text-primary-foreground','shadow-md'];
var _fw_active_caption = ['bg-gradient-to-br','from-primary','to-primary','border-primary','text-primary-foreground','shadow-md'];
var _compatible_formats = __COMPATIBLE_JSON__;
var _format_ui = window.__FORMAT_UI_JSON__ || {};

function applyFormatCompatibility() {
  var name = document.getElementById('new-project-type').value;
  var compat = _compatible_formats[name] || [];
  var fmt = document.getElementById('new-project-format');
  if (!fmt) return;
  document.querySelectorAll('.fmt-btn').forEach(function(b) {
    b.style.display = compat.indexOf(b.getAttribute('data-format')) === -1 ? 'none' : '';
  });
  if (compat.indexOf(fmt.value) === -1 && compat.length > 0) {
    fmt.value = compat[0];
  }
  syncFormatButtons();
  var capField = document.getElementById('new-project-caption-field');
  if (capField) {
    capField.style.display = _format_ui[fmt.value] ? '' : 'none';
  }
}

function syncFormatButtons() {
  var fmt = document.getElementById('new-project-format');
  if (!fmt) return;
  document.querySelectorAll('.fmt-btn').forEach(function(b) {
    var on = b.getAttribute('data-format') === fmt.value;
    _fw_active_format.forEach(function(c) { b.classList.remove(c); });
    _fw_inactive_classes.forEach(function(c) { b.classList.remove(c); });
    (on ? _fw_active_format : _fw_inactive_classes).forEach(function(c) { b.classList.add(c); });
  });
}

function syncCaptionButtons() {
  var sel = document.getElementById('new-project-caption-style');
  if (!sel) return;
  document.querySelectorAll('.cap-btn').forEach(function(b) {
    var on = b.getAttribute('data-style') === sel.value;
    _fw_active_caption.forEach(function(c) { b.classList.remove(c); });
    _fw_inactive_classes.forEach(function(c) { b.classList.remove(c); });
    (on ? _fw_active_caption : _fw_inactive_classes).forEach(function(c) { b.classList.add(c); });
  });
}

function setFormat(name) {
  document.getElementById('new-project-format').value = name;
  applyFormatCompatibility();
  syncFormatButtons();
  mirrorPreview();
}

function setCaptionStyle(name) {
  var sel = document.getElementById('new-project-caption-style');
  if (!sel) return;
  sel.value = name;
  syncCaptionButtons();
  mirrorPreview();
}

function selectFramework(name) {
  document.querySelectorAll('.type-btn').forEach(function(b) {
    var t = b.getAttribute('data-type');
    var active = _fw_active_classes[t] || [];
    active.forEach(function(c) { b.classList.remove(c); });
    _fw_inactive_classes.forEach(function(c) { b.classList.add(c); });
  });
  var selected = document.getElementById('type-btn-' + name);
  if (selected) {
    _fw_inactive_classes.forEach(function(c) { selected.classList.remove(c); });
    var active = _fw_active_classes[name] || ['bg-gradient-to-br','from-primary','to-primary','border-primary','text-primary-foreground','shadow-md'];
    active.forEach(function(c) { selected.classList.add(c); });
  }
  document.getElementById('new-project-type').value = name;
  applyFormatCompatibility();
  mirrorPreview();
}

function switchCreateTab(name) {
  document.querySelectorAll('.create-tab-panel').forEach(function(p) {
    var on = p.getAttribute('data-create-tab') === name;
    p.classList.toggle('hidden', !on);
  });
  var active = ['text-primary','border-primary','bg-card/60'];
  var inactive = ['text-muted-foreground','border-transparent','hover:text-foreground','hover:border-border'];
  document.querySelectorAll('#create-tabs button[data-create-tab]').forEach(function(b) {
    var on = b.getAttribute('data-create-tab') === name;
    active.forEach(function(c) { b.classList.toggle(c, on); });
    inactive.forEach(function(c) { b.classList.toggle(c, !on); });
  });
}

applyFormatCompatibility();
