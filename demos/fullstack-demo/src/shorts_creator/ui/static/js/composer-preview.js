function _pvSetAnchor(blockEl, anchor) {
  if (!blockEl) return;
  var h = blockEl.offsetHeight || 120;
  if (anchor === 'lower_third') {
    blockEl.style.top = Math.round(0.66 * _preview_h - h / 2) + 'px';
  } else {
    blockEl.style.top = Math.round((_preview_h - h) / 2) + 'px';
  }
}

var _pvBoundForm = null;

var _pvTouchedStages = {};

function _pvInitPage() {
  var form = document.getElementById('new-project-format');
  if (!form) return;
  if (_pvBoundForm === form) return;
  _pvBoundForm = form;
  mirrorPreview();
  _pvPositionTicks();
  buildSectionToggles();
  document.querySelectorAll('#new-project-stages .stage-toggle').forEach(function(cb) {
    cb.addEventListener('change', function() {
      var sk = cb.getAttribute('data-stage');
      if (sk) _pvTouchedStages[sk] = true;
      _pvKnobChanged();
    });
  });
  syncComposerHidden();
  document.querySelectorAll('#new-project-anchor .anchor-btn').forEach(function(b) {
    b.addEventListener('click', function() {
      document.querySelectorAll('#new-project-anchor .anchor-btn').forEach(function(x) {
        x.classList.remove('bg-primary', 'text-primary-foreground');
        x.classList.add('bg-secondary', 'text-foreground');
      });
      b.classList.remove('bg-secondary', 'text-foreground');
      b.classList.add('bg-primary', 'text-primary-foreground');
      syncComposerHidden();
      mirrorPreview();
    });
  });
  _pvBindSegments('new-project-motion', '.motion-btn');
  _pvBindSegments('new-project-emphasis', '.emphasis-btn');
  document.querySelectorAll('.accent-chip').forEach(function(c) {
    c.addEventListener('click', function() {
      var wrap = c.parentElement;
      wrap.querySelectorAll('.accent-chip').forEach(function(x) {
        x.classList.remove('ring-2', 'ring-primary', 'ring-offset-1');
        x.classList.add('ring-1', 'ring-border');
      });
      c.classList.remove('ring-1', 'ring-border');
      c.classList.add('ring-2', 'ring-primary', 'ring-offset-1');
      syncComposerHidden();
      mirrorPreview();
    });
  });
  var presetSelect = document.getElementById('preset-select');
  if (presetSelect && !presetSelect.dataset.bound) {
    presetSelect.dataset.bound = '1';
    _presetsRefresh(presetSelect);
  }
}

function _pvBindSegments(containerId, btnSel) {
  document.querySelectorAll('#' + containerId + ' ' + btnSel).forEach(function(b) {
    b.addEventListener('click', function() {
      document.querySelectorAll('#' + containerId + ' ' + btnSel).forEach(function(x) {
        x.classList.remove('bg-primary', 'text-primary-foreground');
        x.classList.add('bg-secondary', 'text-foreground');
      });
      b.classList.remove('bg-secondary', 'text-foreground');
      b.classList.add('bg-primary', 'text-primary-foreground');
      syncComposerHidden();
      mirrorPreview();
    });
  });
}

function resetComposerKnob(id) {
  var widget = document.getElementById(id);
  if (!widget) return;
  var def = widget.getAttribute('data-builtin');
  if (def === null) def = widget.getAttribute('data-default');
  if (def === null) return;
  widget.value = def;
  _pvKnobChanged();
}

function _pvKnobChanged() {
  syncComposerHidden();
  mirrorPreview();
}

document.addEventListener('DOMContentLoaded', _pvInitPage);
document.addEventListener('htmx:load', _pvInitPage);
if (document.readyState !== 'loading') _pvInitPage();
['new-project-format','new-project-duration',
 'new-project-caption-style','new-project-type','new-project-pacing','new-project-hook-text',
 'new-project-chunk-size','new-project-highlight-colour','new-project-pill-colour',
 'new-project-caption-size','new-project-outline-width','new-project-block-width',
 'new-project-numbered-scale','new-project-pill-mode','new-project-uppercase',
 'new-project-scrim','new-project-watermark-corner','new-project-watermark-size',
 'new-project-watermark-opacity','new-project-music-volume','new-project-music-fade',
 'new-project-fade-out','new-project-motion','new-project-emphasis',
 'new-project-loudness','new-project-audio-normalize',
 'new-project-hold-hook','new-project-message-pacing','new-project-hold-conclusion',
'new-project-stage-accent-hook','new-project-stage-accent-message',
  'new-project-stage-accent-metaphor','new-project-stage-accent-conclusion',
  'new-project-asset-bg_clip-source','new-project-asset-bg_clip','new-project-asset-bg_clip-url',
  'new-project-asset-bg_clip-provider',
  'new-project-asset-music-source','new-project-asset-music','new-project-asset-music-url',
  'new-project-asset-outro_clip-source','new-project-asset-outro_clip','new-project-asset-outro_clip-url',
  'new-project-asset-watermark-source','new-project-asset-watermark','new-project-asset-watermark-url',
  'new-project-asset-font'].forEach(function(id) {
  var elNode = document.getElementById(id);
  if (!elNode) return;
  elNode.addEventListener('input', _pvKnobChanged);
  elNode.addEventListener('change', _pvKnobChanged);
});

function _pvUpdateOutroText() {
  var span = document.getElementById('preview-outro-text');
  if (!span) return;
  var ot = document.getElementById('new-project-outro-text');
  var text = ot && ot.value.trim() !== '' ? ot.value.trim() : 'Thanks for watching';
  span.textContent = text;
}

var outroField = document.getElementById('new-project-outro-text');
if (outroField) outroField.addEventListener('input', _pvUpdateOutroText);
function toggleBgMode(radio) {
    var wrapper = document.getElementById('bg-clip-picker-wrapper');
    if (!wrapper) return;
    var image = radio.value === 'image';
    var label = wrapper.querySelector('label');
    if (label) label.textContent = image ? 'Background image' : 'Background clip';
    var source = document.getElementById('new-project-asset-bg_clip-source');
    if (!source || !source.options) return;
    var apiOption = null;
    for (var i = 0; i < source.options.length; i++) {
        if (source.options[i].value === 'api') apiOption = source.options[i];
    }
    if (!apiOption) return;
    apiOption.hidden = image;
    if (image && source.value === 'api') {
        source.value = 'assets';
        if (typeof toggleMediaSource === 'function') toggleMediaSource(source);
    }
}
