var _preview_data = __PREVIEW_JSON__ = __PREVIEW_DATA_OBJ__;
var _prevAccents = [];
var _preview_w = 360;
var _preview_h = 640;

function _pvTokenCssValue(varName, fallback) {
  var raw = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return raw || fallback;
}

function _pvOklchToRgb01(L, C, h) {
  var hr = h * Math.PI / 180;
  var a = C * Math.cos(hr), b = C * Math.sin(hr);
  var l_ = L + a * 0.3963377774 + b * 0.2158037573;
  var m_ = L - a * 0.1055613458 - b * 0.0638541728;
  var s_ = L - a * 0.0894841775 - b * 1.2914855480;
  l_ = l_ * l_ * l_; m_ = m_ * m_ * m_; s_ = s_ * s_ * s_;
  return [
    4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
    -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
    -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
  ];
}

function _pvTokenHex(varName, fallback) {
  var raw = _pvTokenCssValue(varName, '');
  if (!raw) return fallback;
  if (raw.charAt(0) === '#') {
    var hx = raw.replace('#', '');
    if (hx.length === 3) hx = hx.replace(/(.)/g, '$1$1');
    if (hx.length === 6) return '0x' + (hx + 'FF').toUpperCase();
    return '0x' + hx.toUpperCase();
  }
  var m = raw.match(/oklch\(([\d.]+)\s+([\d.]+)\s+([\d.]+)/);
  if (m) {
    var rgb = _pvOklchToRgb01(parseFloat(m[1]), parseFloat(m[2]), parseFloat(m[3]));
    var hex = '';
    for (var i = 0; i < 3; i++) {
      var c = 1.055 * Math.pow(Math.max(0, Math.min(1, rgb[i])), 1 / 2.4) - 0.055;
      var v = Math.round(c * 255);
      hex += (v < 16 ? '0' : '') + v.toString(16);
    }
    return '0x' + (hex + 'FF').toUpperCase();
  }
  return fallback;
}

function _pvFitHookFont(texts, widthFactor, highlightColour) {
  var maxChars = 0;
  for (var i = 0; i < texts.length; i++) maxChars = Math.max(maxChars, texts[i].length);
  var wf = widthFactor || 0.80;
  var widthFit = (wf * 1080) / (maxChars * 0.55);
  var heightFit = (0.70 * 1920) / (texts.length * 1.3);
  var size = Math.max(40, Math.min(110, widthFit, heightFit));
  return Math.round(size * 360 / 1080 * 100) / 100;
}

function _pvHexToRgba(hex6, alpha) {
  var r = parseInt(hex6.slice(0, 2), 16), g = parseInt(hex6.slice(2, 4), 16), b = parseInt(hex6.slice(4, 6), 16);
  return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + alpha + ')';
}

function _pvPillBg() {
  var pb = document.getElementById('new-project-pill-colour');
  var hex = pb ? pb.value.replace('#', '') : '000000';
  if (hex.length === 3) hex = hex.replace(/(.)/g, '$1$1');
  return _pvHexToRgba(hex, '0.75');
}

function _pvHighlightBg() {
  var pc = document.getElementById('new-project-highlight-colour');
  var hex = pc ? pc.value.replace('#', '') : '7c5cfa';
  if (hex.length === 3) hex = hex.replace(/(.)/g, '$1$1');
  return _pvHexToRgba(hex, '1');
}

function _pvCaptionFontSize() {
  var csize = document.getElementById('new-project-caption-size');
  return csize ? (parseInt(csize.value, 10) * 360 / 1080) : (56 * 360 / 1080);
}

function _pvCaptionOutline() {
  var outline = document.getElementById('new-project-outline-width');
  return outline ? parseInt(outline.value, 10) : 2;
}

var _pvBuiltCaptionFormat = null;

function _buildCaptionField() {
  var field = document.getElementById('new-project-caption-field');
  if (!field) return;
  var fmt = document.getElementById('new-project-format');
  var fmtName = fmt ? fmt.value : 'narrated';
  if (_pvBuiltCaptionFormat === fmtName) return;
  _pvBuiltCaptionFormat = fmtName;
  var ui = window.__FORMAT_UI_JSON__ || {};
  var spec = ui[fmtName];
  if (!spec) {
    field.style.display = 'none';
    return;
  }
  var sel = document.getElementById('new-project-caption-style');
  var keep = sel ? sel.value : '';
  var valid = false;
  for (var i = 0; i < spec.options.length; i++) {
    if (String(spec.options[i][0]) === keep) { valid = true; break; }
  }
  var value = valid ? keep : String(spec.options[0][0]);
  var active = ['bg-gradient-to-br', 'from-primary', 'to-primary', 'border-primary', 'text-primary-foreground', 'shadow-md'];
  var inactive = ['bg-card/60', 'border-border', 'text-muted-foreground'];

  field.style.display = '';
  field.innerHTML = '';
  var label = document.createElement('label');
  label.setAttribute('for', 'new-project-caption-style');
  label.className = 'block text-xs font-semibold text-foreground mb-1.5 font-mono';
  label.textContent = 'Caption Style';
  field.appendChild(label);

  var select = document.createElement('select');
  select.id = 'new-project-caption-style';
  select.name = 'caption_style';
  select.className = 'hidden';
  for (var i = 0; i < spec.options.length; i++) {
    var opt = document.createElement('option');
    opt.value = spec.options[i][0];
    opt.textContent = spec.options[i][1];
    if (String(spec.options[i][0]) === value) opt.selected = true;
    select.appendChild(opt);
  }
  select.value = value;
  field.appendChild(select);
  select.addEventListener('input', _pvKnobChanged);
  select.addEventListener('change', _pvKnobChanged);

  var row = document.createElement('div');
  row.className = 'flex gap-2 overflow-x-auto pb-1';
  for (var i = 0; i < spec.options.length; i++) {
    (function (v, lbl) {
      var b = document.createElement('div');
      b.id = 'cap-btn-' + (v === '' ? 'none' : v);
      b.className = 'shrink-0 cap-btn flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 border cursor-pointer select-none ';
      b.setAttribute('data-style', v);
      b.setAttribute('onclick', "setCaptionStyle('" + v + "')");
      b.textContent = lbl;
      (v === value ? active : inactive).forEach(function (c) { b.classList.add(c); });
      row.appendChild(b);
    })(spec.options[i][0], spec.options[i][1]);
  }
  field.appendChild(row);

  var err = document.createElement('div');
  err.id = 'profile-field-error-caption_style';
  err.className = 'profile-error-slot';
  field.appendChild(err);

  var help = document.createElement('p');
  help.className = 'text-muted-foreground text-[11px] mt-1.5 font-mono';
  help.textContent = spec.help;
  field.appendChild(help);
}

function _pvLiveHookText() {
  var hk = document.getElementById('new-project-hook-text');
  if (hk && hk.value.trim() !== '') return hk.value.trim();
  var specNode = document.getElementById('spec-json');
  if (specNode) {
    try {
      var saved = JSON.parse(specNode.textContent);
      if (saved && saved.hook_text) return saved.hook_text;
    } catch (e) { /* fall through to skeleton */ }
  }
  return '';
}

function mirrorPreview() {
  var title = document.getElementById('new-project-title');
  var fmt = document.getElementById('new-project-format');
  var dur = document.getElementById('new-project-duration');
  var type = document.getElementById('new-project-type');
  if (!title) return;

  _buildCaptionField();
  var cap = document.getElementById('new-project-caption-style');
  var fmtName = fmt ? fmt.value : 'narrated';
  var info = _preview_data.formats[fmtName] || _preview_data.formats.narrated;

  var hookBlock = document.getElementById('preview-hook-block');
  if (hookBlock) {
    var hookText = _pvLiveHookText();
    var hookRow = hookText !== '' ? null : (info.skeleton || []).filter(function(r) { return r.label === 'Hook'; })[0];
    var hookWords = hookText !== '' ? hookText.split(/[ \t]+/) : (hookRow ? hookRow.text.split(/[ \t]+/) : []);
    hookBlock.innerHTML = '';
    var bw = document.getElementById('new-project-block-width');
    var wf = bw ? (parseInt(bw.value, 10) / 100) : 0.80;
    var layoutData = info.layout || {};
    var hookFont = _pvFitHookFont(hookWords, wf, (info.palette || {}).highlight_colour || _pvTokenHex('--primary', '0x7C5CFAFF'));
    for (var i = 0; i < hookWords.length; i++) {
      var s = document.createElement('span');
      s.className = 'pv-hook block';
      s.style.fontSize = hookFont + 'px';
      s.style.background = _pvPillBg();
      s.textContent = hookWords[i];
      hookBlock.appendChild(s);
    }
    _pvSetAnchor(hookBlock, layoutData.anchor || 'center');
  }

  var activeSkeleton = fmtName === 'topn' ? 'preview-skeleton-topn' : 'preview-skeleton-narrated';
  document.querySelectorAll('.preview-skeleton').forEach(function(s) {
    s.style.display = s.id === activeSkeleton ? '' : 'none';
  });

  if (fmtName !== 'topn') {
    var topicInfo = _preview_data.topics[type ? type.value : ''] || _preview_data.topics.self_improvement;
    var liveSec = [];
    var secJson = document.getElementById('new-project-sections');
    if (secJson && secJson.value) {
      try { liveSec = JSON.parse(secJson.value); } catch (e) { liveSec = []; }
    }
    var midSections = (liveSec.length ? liveSec : (topicInfo.sections || [])).filter(function(s) {
      return s !== 'hook' && s !== 'conclusion' && s !== 'top_items';
    });
    var midLabels = document.querySelectorAll('#preview-skeleton-narrated .skel-mid-label');
    for (var i = 0; i < midLabels.length; i++) {
      midLabels[i].textContent = i < midSections.length ? midSections[i] : '';
    }
  }

  var capField = document.getElementById('preview-caption');
  if (capField) {
    capField.style.display = info.caption_styles.length === 0 ? 'none' : '';
  }
  _pvStyleLess = info.caption_styles.length === 0 && !info.rank;
  _pvSetDisplay('preview-hook-block', _pvStyleLess ? 'none' : '');
  _pvSetDisplay('preview-ranking-block', !!info.rank);
  if (cap && capField) {
    var capVal = cap.value;
    if (capVal !== 'highlight' && capVal !== 'plain') capVal = 'highlight';
    document.getElementById('preview-caption-highlight').style.display =
      capVal === 'highlight' ? '' : 'none';
    document.getElementById('preview-caption-plain').style.display =
      capVal === 'plain' ? '' : 'none';
  }
  if (!_pvPlaying) {
    if (!!info.rank) {
      if (_pvListMode()) _pvRenderRankingList();
      else _pvRenderRanking(0);
    } else if (info.caption_styles.length) {
      var seedChunks = _pvCaptionChunks();
      if (seedChunks.length) _pvRenderCaption(seedChunks[0], 0);
    }
  }

  var raw = dur ? parseFloat(dur.value) : NaN;
  var fill = 0;
  if (!isNaN(raw) && info.duration_range && info.duration_range[1] > info.duration_range[0]) {
    var lo = info.duration_range[0], hi = info.duration_range[1];
    fill = Math.max(0, Math.min(1, (raw - lo) / (hi - lo)));
  }
  document.getElementById('preview-duration-fill').style.width = Math.round(fill * 100) + '%';

  var hint = document.getElementById('duration-range-hint');
  if (hint) {
    var rng = info.duration_range || [30, 60];
    hint.textContent = (info.label || fmtName) + ' renders ' + rng[0] + '\u2013' + rng[1] + 's';
    hint.style.color = (!isNaN(raw) && (raw < rng[0] || raw > rng[1])) ? 'rgb(var(--color-warning-channels))' : '';
  }

  var meta = _preview_data.topics[type ? type.value : ''] || _preview_data.topics.self_improvement;
  var phone = document.getElementById('preview-topic-dot');
  if (phone && meta.active_classes) {
    _prevAccents.forEach(function(c) { phone.classList.remove(c); });
    meta.active_classes.forEach(function(c) { phone.classList.add(c); });
    _prevAccents = meta.active_classes;
  }
}

var _pvIntroFrac = 0.15;  // hook screen share of the reel (pipeline line 0)
var _pvOutroFrac = 0.10;  // outro clip share (pipeline outro_seconds / total)
var _pvMode = 'full';
var _pvPlaying = false;
var _pvProgress = 0;
var _pvTimer = null;
var _pvStyleLess = false;

function _pvSetDisplay(id, show) {
  var elNode = document.getElementById(id);
  if (elNode) elNode.style.display = show ? '' : 'none';
}

function _pvTotalSeconds() {
  var dur = document.getElementById('new-project-duration');
  var v = dur ? parseFloat(dur.value) : NaN;
  return isNaN(v) || v <= 0 ? 30 : v;
}

function _pvCaptionChunks() {
  var fmt = document.getElementById('new-project-format');
  var fmtName = fmt ? fmt.value : 'narrated';
  var skel = (_preview_data.formats[fmtName] || {}).skeleton || [];
  return skel
    .filter(function(r) { return r.label !== 'Hook' && r.text; })
    .map(function(r) { return r.text.split(' '); });
}

function _pvWindowLen() {
  if (_pvMode === 'full') return 1;
  if (_pvMode === 'intro') return _pvIntroFrac;
  if (_pvMode === 'outro') return _pvOutroFrac;
  return 1 - _pvIntroFrac - _pvOutroFrac;
}

function _pvBarProgress() {
  if (_pvMode === 'full') return _pvProgress;
  if (_pvMode === 'intro') return _pvIntroFrac * _pvProgress;
  if (_pvMode === 'outro') return (1 - _pvOutroFrac) + _pvOutroFrac * _pvProgress;
  return _pvIntroFrac + _pvWindowLen() * _pvProgress;
}

function _pvRenderFrame() {
  var p = _pvProgress;
  var fill = document.getElementById('preview-duration-fill');
  if (fill) fill.style.width = Math.round(_pvBarProgress() * 100) + '%';
  _pvUpdatePositionDisplay();

  var midStart = _pvMode === 'full' ? _pvIntroFrac : 0;
  var midLen = _pvMode === 'full' ? 1 - _pvIntroFrac - _pvOutroFrac : 1;

  if (_pvMode === 'intro' || (_pvMode === 'full' && p < midStart)) {
    _pvShowOnly('hook');
    return;
  }
  if (_pvMode === 'outro' || (_pvMode === 'full' && p >= midStart + midLen)) {
    _pvShowOnly('outro');
    return;
  }
  _pvShowOnly('mid');
  var frac = midLen > 0 ? (p - midStart) / midLen : 0;
  if (_pvRankMode()) {
    if (_pvListMode()) {
      _pvRenderRankingList();
      return;
    }
    var items = _pvRankItems();
    if (!items.length) return;
    _pvRenderRanking(Math.min(items.length - 1, Math.floor(frac * items.length)));
    return;
  }
  var chunks = _pvCaptionChunks();
  if (!chunks.length) return;
  var ci = Math.min(chunks.length - 1, Math.floor(frac * chunks.length));
  var words = chunks[ci];
  var wi = Math.min(words.length - 1, Math.floor(((frac * chunks.length) % 1) * words.length));
  _pvRenderCaption(words, wi);
}

function _pvTick() {
  if (!_pvPlaying) return;
  _pvProgress += 0.1 / (_pvTotalSeconds() * _pvWindowLen());
  if (_pvProgress >= 1) {
    _pvProgress = 0;
    var video = document.getElementById('preview-bg-video');
    if (video && video.currentTime) video.currentTime = 0;
  }
  _pvRenderFrame();
}

function _pvSetPlayingUI() {
  _pvSetDisplay('preview-play-icon', !_pvPlaying);
  _pvSetDisplay('preview-pause-icon', _pvPlaying);
}

function _pvSyncVideo() {
  var video = document.getElementById('preview-bg-video');
  if (!video) return;
  if (_pvPlaying) {
    if (typeof video.play === 'function' && video.paused) video.play();
  } else if (typeof video.pause === 'function' && !video.paused) {
    video.pause();
  }
}

function _pvFmtTime(sec) {
  var s = Math.max(0, Math.floor(sec));
  return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2);
}

function _pvUpdatePositionDisplay() {
  var elNode = document.getElementById('preview-position-display');
  if (!elNode) return;
  var frac = Math.min(1, Math.max(0, _pvProgress));
  var total = _pvTotalSeconds();
  elNode.textContent = _pvFmtTime(frac * total) + ' / ' + _pvFmtTime(total);
}

function togglePreviewPlay() {
  _pvPlaying = !_pvPlaying;
  if (_pvPlaying) {
    if (!_pvTimer) _pvTimer = setInterval(_pvTick, 100);
  } else if (_pvTimer) {
    clearInterval(_pvTimer);
    _pvTimer = null;
  }
  _pvSetPlayingUI();
  _pvSyncVideo();
  _pvRenderFrame();
  _pvUpdatePositionDisplay();
}

function _pvShowOnly(which) {
  _pvSetDisplay('preview-bg-layer', which !== 'outro');
  _pvSetDisplay('preview-hook-block', !_pvStyleLess && which === 'hook');
  _pvSetDisplay('preview-mid-block', !_pvStyleLess && which === 'mid');
  _pvSetDisplay('preview-ranking-block', _pvRankMode() && which === 'mid');
  _pvSetDisplay('preview-outro', which === 'outro');
  _pvSetDisplay('preview-duration-bar', _pvPlaying || _pvProgress > 0 || _pvMode === 'full');
}

function _pvRenderCaption(words, wordIdx) {
  var hl = document.getElementById('preview-caption-highlight');
  var pl = document.getElementById('preview-caption-plain');
  if (!hl || !pl) return;
  var capFont = _pvCaptionFontSize();
  var outline = _pvCaptionOutline();
  hl.innerHTML = words.map(function(w, i) {
    return '<span class="pv-cap' + (i === wordIdx ? ' pv-pill' : '') + '">' + w + '</span>';
  }).join('');
  var spans = hl.querySelectorAll('span.pv-cap');
  var pillBg = _pvHighlightBg();
  for (var i = 0; i < spans.length; i++) {
    spans[i].style.fontSize = capFont + 'px';
    spans[i].style.WebkitTextStroke = outline + 'px #000';
    if (spans[i].classList.contains('pv-pill')) spans[i].style.background = pillBg;
  }
  pl.style.fontSize = capFont + 'px';
  pl.style.WebkitTextStroke = outline + 'px #000';
  pl.textContent = words.join(' ');
}

function _pvRankMode() {
  var fmt = document.getElementById('new-project-format');
  var fmtName = fmt ? fmt.value : 'narrated';
  return !!((_preview_data.formats[fmtName] || {}).rank);
}

function _pvListMode() {
  var cap = document.getElementById('new-project-caption-style');
  return _pvRankMode() && !!cap && cap.value === 'list';
}

function _pvRankItems() {
  var fmt = document.getElementById('new-project-format');
  var fmtName = fmt ? fmt.value : 'narrated';
  return ((_preview_data.formats[fmtName] || {}).skeleton || [])
    .filter(function(r) { return r.num && r.text; })
    .map(function(r) {
      return {
        num: r.num,
        words: r.text.split(/[ \t]+/).map(function(w) { return w.replace(/[.,;:!?]+$/, ''); })
      };
    });
}

function _pvRenderRanking(idx) {
  var block = document.getElementById('preview-ranking-block');
  if (!block) return;
  var items = _pvRankItems();
  if (!items.length) return;
  var item = items[Math.min(items.length - 1, Math.max(0, idx))];
  var pillFont = _pvFitHookFont([item.num].concat(item.words));
  var ns = document.getElementById('new-project-numbered-scale');
  var scale = ns ? parseFloat(ns.value) : 1.6;
  var numFont = Math.round(pillFont * scale * 100) / 100;
  block.innerHTML = '';
  var n = document.createElement('span');
  n.className = 'pv-hook block';
  n.style.fontSize = numFont + 'px';
  n.style.background = _pvPillBg();
  n.textContent = item.num;
  block.appendChild(n);
  for (var i = 0; i < item.words.length; i++) {
    var s = document.createElement('span');
    s.className = 'pv-hook block';
    s.style.fontSize = pillFont + 'px';
    s.style.background = _pvPillBg();
    s.textContent = item.words[i];
    block.appendChild(s);
  }
  var fmt = document.getElementById('new-project-format');
  var fmtName = fmt ? fmt.value : 'narrated';
  var layoutData = (_preview_data.formats[fmtName] || {}).layout || {};
  _pvSetAnchor(block, layoutData.anchor || 'center');
}

function _pvRenderRankingList() {
  var block = document.getElementById('preview-ranking-block');
  if (!block) return;
  var items = _pvRankItems();
  if (!items.length) return;
  var rows = items.map(function(it) { return it.num + '. ' + it.words.join(' '); });
  var pillFont = _pvFitHookFont(rows);
  block.innerHTML = '';
  for (var i = 0; i < rows.length; i++) {
    var s = document.createElement('span');
    s.className = 'pv-hook block';
    s.style.fontSize = pillFont + 'px';
    s.style.background = _pvPillBg();
    s.textContent = rows[i];
    block.appendChild(s);
  }
  var fmt = document.getElementById('new-project-format');
  var fmtName = fmt ? fmt.value : 'narrated';
  var layoutData = (_preview_data.formats[fmtName] || {}).layout || {};
  _pvSetAnchor(block, layoutData.anchor || 'center');
}

function _pvPositionTicks() {
  var ticks = document.getElementById('preview-timeline-ticks');
  if (!ticks || ticks.children.length < 2) return;
  ticks.children[0].style.left = Math.round(_pvIntroFrac * 100) + '%';
  ticks.children[1].style.left = Math.round((1 - _pvOutroFrac) * 100) + '%';
}

function setPreviewSection(name) {
  var states = {
    intro: { bg: true, hook: true, mid: false, dur: false, outro: false },
    mid: { bg: true, hook: false, mid: true, dur: false, outro: false },
    outro: { bg: false, hook: false, mid: false, dur: false, outro: true },
    full: { bg: true, hook: true, mid: true, dur: true, outro: false },
  };
  var s = states[name] || states.full;
  _pvSetDisplay('preview-bg-layer', s.bg);
  _pvSetDisplay('preview-hook-block', s.hook && !_pvStyleLess);
  _pvSetDisplay('preview-mid-block', s.mid && !_pvStyleLess);
  _pvSetDisplay('preview-ranking-block', s.mid && _pvRankMode());
  _pvSetDisplay('preview-duration-bar', s.dur);
  _pvSetDisplay('preview-outro', s.outro);
  document.querySelectorAll('#preview-section-tabs button').forEach(function(b) {
    var on = b.getAttribute('data-preview-section') === name;
    b.classList.toggle('bg-primary', on);
    b.classList.toggle('text-primary-foreground', on);
    b.classList.toggle('bg-secondary/80', !on);
    b.classList.toggle('text-muted-foreground', !on);
    b.classList.toggle('hover:bg-secondary', !on);
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
  _pvMode = name;
  _pvProgress = 0;
  if (!_pvPlaying) togglePreviewPlay();
  _pvRenderFrame();
}

function buildSectionToggles() {
  var row = document.getElementById('section-toggle-row');
  if (!row) return;
  var type = document.getElementById('new-project-type');
  var topicName = type ? type.value : 'self_improvement';
  var topic = _preview_data.topics[topicName] || _preview_data.topics.self_improvement;
  var stored = document.getElementById('new-project-sections');
  var storedSections = [];
  if (stored && stored.value) {
    try { storedSections = JSON.parse(stored.value); } catch (e) { storedSections = []; }
  }
  var names = storedSections.length ? storedSections : (topic.sections || []);
  row.innerHTML = '';
  names.forEach(function(name) {
    if (name === 'hook' || name === 'conclusion' || name === 'top_items') return;
    var label = document.createElement('label');
    label.className = 'flex items-center gap-1.5 text-[11px] text-foreground';
    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = name;
    cb.checked = true;
    cb.className = 'accent-primary section-toggle';
    cb.addEventListener('change', _pvKnobChanged);
    label.appendChild(cb);
    label.appendChild(document.createTextNode(name));
    row.appendChild(label);
  });
}

function _pvUpdateReadouts() {
  var defs = {
    'new-project-hold-hook': 's',
    'new-project-message-pacing': 's/line',
    'new-project-hold-conclusion': 's',
    'new-project-loudness': 'LUFS'
  };
  for (var id in defs) {
    var widget = document.getElementById(id);
    var readout = document.getElementById(id + '-readout');
    if (!widget || !readout) continue;
    var v = widget.value === '' ? (widget.getAttribute('data-default') || '') : widget.value;
    readout.textContent = v + ' ' + defs[id];
  }
}

var _PV_MEDIA_ROLES = [
  ['bg_clip', 'Background'],
  ['music', 'Music'],
  ['outro_clip', 'Outro'],
  ['watermark', 'Watermark']
];

function _pvPrettifyKey(name) {
  return String(name).replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); });
}

function _pvMediaLine(role, label) {
  var source = document.getElementById('new-project-asset-' + role + '-source');
  var asset = document.getElementById('new-project-asset-' + role);
  var url = document.getElementById('new-project-asset-' + role + '-url');
  var provider = document.getElementById('new-project-asset-' + role + '-provider');
  var mode = source ? source.value : 'assets';
  var value = '';
  if (mode === 'url' && url && url.value) {
    try { value = 'URL ' + new URL(url.value).hostname; } catch (e) { value = 'URL ' + url.value; }
  } else if (mode === 'api' && provider) {
    value = 'API ' + (provider.selectedOptions[0] ? provider.selectedOptions[0].textContent : 'auto');
  } else if (asset && asset.selectedOptions[0] && asset.selectedOptions[0].value !== '') {
    value = asset.selectedOptions[0].textContent;
  }
  return value ? [[label, value]] : [];
}

function _pvSummaryRows(spec) {
  var rows = [];
  var fmt = _preview_data.formats[spec.format_name || 'narrated'] || _preview_data.formats.narrated;

  var cap = document.getElementById('new-project-caption-style');
  var capLabel = cap && cap.selectedOptions[0] ? cap.selectedOptions[0].textContent : '';
  var typeEl = document.getElementById('new-project-type');
  var typeName = typeEl ? typeEl.value : 'self_improvement';
  var topic = _preview_data.topics[typeName] || _preview_data.topics.self_improvement;
  rows.push(['Format', (((fmt.label || spec.format_name || 'narrated')) + (capLabel ? ' \u00b7 ' + capLabel : ''))]);
  rows.push(['Topic', ((topic.emoji || '') + ' ' + _pvPrettifyKey(typeName))]);

  var dur = spec.duration_seconds;
  if (typeof dur === 'number') {
    var rng = fmt.duration_range;
    if (rng && rng[1] > rng[0]) dur = Math.max(rng[0], Math.min(rng[1], dur));
    var durText = '~' + Math.round(dur) + 's';
    if (rng && rng[1] > rng[0]) durText += ' (' + rng[0] + '\u2013' + rng[1] + 's range)';
    rows.push(['Duration', durText]);
  }
  if (typeof spec.pacing_wps === 'number') rows.push(['Pacing', spec.pacing_wps + ' wps']);

  var style = spec.style || {};
  var stBits = [];
  if (typeof style.chunk_size === 'number') stBits.push(style.chunk_size + ' words/line');
  if (typeof style.caption_font_size === 'number') stBits.push(style.caption_font_size + 'px caps');
  if (style.uppercase) stBits.push('UPPERCASE');
  if (spec.emphasis_style === 'accent') stBits.push('accents on');
  else if (spec.emphasis_style === 'scale') stBits.push('scale emphasis');
  else if (spec.emphasis_style === 'off') stBits.push('accents off');
  if (stBits.length) rows.push(['Captions', stBits.join(' \u00b7 ')]);

  if (spec.hook_text) rows.push(['Hook', spec.hook_text]);

  var extra = [];
  if (spec.background_motion && spec.background_motion !== 'none') extra.push('motion ' + spec.background_motion);
  var holds = spec.section_holds || {};
  var holdBits = [];
  if (typeof holds.hook === 'number') holdBits.push('hook ' + holds.hook + 's');
  if (typeof holds.message === 'number') holdBits.push('message ' + holds.message + 's');
  if (typeof holds.conclusion === 'number') holdBits.push('conclusion ' + holds.conclusion + 's');
  if (holdBits.length) extra.push('holds ' + holdBits.join('/'));
  var accents = spec.stage_accents || {};
  var accentCount = 0;
  for (var a in accents) if (accents[a]) accentCount++;
  if (accentCount) extra.push(accentCount + ' stage accent' + (accentCount > 1 ? 's' : ''));
  if (spec.loudness_target_lufs) extra.push(spec.loudness_target_lufs + ' LUFS');
  if (spec.audio_normalize === true) extra.push('loudnorm');
  if (extra.length) rows.push(['Motion & audio', extra.join(' \u00b7 ')]);

  var media = [];
  for (var i = 0; i < _PV_MEDIA_ROLES.length; i++) {
    media = media.concat(_pvMediaLine(_PV_MEDIA_ROLES[i][0], _PV_MEDIA_ROLES[i][1]));
  }
  var fontSel = document.getElementById('new-project-asset-font');
  if (fontSel && fontSel.selectedOptions[0] && fontSel.selectedOptions[0].value !== '') {
    media.push(['Font', fontSel.selectedOptions[0].textContent]);
  }
  if (media.length) {
    rows.push(['Media', media.map(function(m) { return m[0] + ' ' + m[1]; }).join(' \u00b7 ')]);
  }

  var stages = spec.stages;
  if (Array.isArray(stages) && stages.length) {
    rows.push(['Stages', stages.length + ' (' + stages.map(_pvPrettifyKey).join(', ') + ')']);
  }
  return rows;
}

function _pvUpdateSummary() {
  var out = document.getElementById('composer-summary');
  if (!out) return;
  var spec = {};
  var specNode = document.getElementById('spec-json');
  if (specNode) {
    try { spec = JSON.parse(specNode.textContent); } catch (e) { spec = {}; }
  }
  var rows = _pvSummaryRows(spec);
  out.innerHTML = '';
  rows.forEach(function(r) {
    var row = document.createElement('div');
    row.className = 'flex items-baseline gap-2 py-0.5';
    var k = document.createElement('span');
    k.className = 'shrink-0 w-24 font-semibold uppercase tracking-wider text-[10px] text-muted-foreground';
    k.textContent = r[0];
    var v = document.createElement('span');
    v.className = 'min-w-0 break-words';
    v.textContent = r[1];
    row.appendChild(k);
    row.appendChild(v);
    out.appendChild(row);
  });
}

var _PV_STRUCT_GROUPS = [
  ['Format & Duration', [['', 'format_name'], ['', 'duration_seconds'], ['', 'pacing_wps'], ['', 'hook_text']]],
  ['Captions & Style', [['style', 'chunk_size'], ['style', 'caption_font_size'], ['style', 'caption_outline_width'], ['style', 'uppercase'], ['style', 'scrim_alpha']]],
  ['Layout', [['layout', 'anchor'], ['layout', 'block_width_pct'], ['layout', 'numbered_scale'], ['layout', 'pill_per_word'], ['layout', 'watermark_corner'], ['layout', 'watermark_size_pct'], ['layout', 'watermark_opacity'], ['layout', 'music_volume'], ['layout', 'music_fade_seconds'], ['layout', 'fade_out_seconds']]],
  ['Motion & Emphasis', [['', 'background_motion'], ['', 'emphasis_style'], ['', 'section_holds'], ['', 'stage_accents']]],
  ['Audio', [['', 'loudness_target_lufs'], ['', 'audio_normalize']]]
];

function _pvStructuredValue(spec, container, key) {
  var obj = container ? (spec[container] || {}) : spec;
  var v = obj[key];
  if (v === undefined || v === null || v === '') return null;
  if (typeof v === 'boolean') return v ? 'on' : 'off';
  if (typeof v === 'object') {
    var bits = [];
    for (var k in v) {
      var val = v[k];
      if (val === undefined || val === null || val === '' || val === false) continue;
      bits.push(_pvPrettifyKey(k) + ' ' + String(val));
    }
    return bits.length ? bits.join(' \u00b7 ') : null;
  }
  if (key === 'format_name') {
    var fmt = _preview_data.formats[v];
    return (fmt && fmt.label) || _pvPrettifyKey(v);
  }
  return String(v);
}

function _pvRenderStructuredSpec(spec) {
  var out = document.getElementById('spec-structured');
  if (!out) return;
  out.innerHTML = '';
  _PV_STRUCT_GROUPS.forEach(function(g) {
    var items = [];
    g[1].forEach(function(entry) {
      var val = _pvStructuredValue(spec, entry[0], entry[1]);
      if (val === null) return;
      items.push([_pvPrettifyKey(entry[1]), val]);
    });
    if (!items.length) return;
    var head = document.createElement('div');
    head.className = 'mt-2 first:mt-0 font-semibold uppercase tracking-wider text-[10px] text-muted-foreground';
    head.textContent = g[0];
    out.appendChild(head);
    items.forEach(function(it) {
      var row = document.createElement('div');
      row.className = 'flex items-baseline gap-2 py-0.5';
      var k = document.createElement('span');
      k.className = 'shrink-0 w-32 text-muted-foreground';
      k.textContent = it[0];
      var v = document.createElement('span');
      v.className = 'min-w-0 break-words';
      v.textContent = it[1];
      row.appendChild(k);
      row.appendChild(v);
      out.appendChild(row);
    });
  });
}

function syncComposerHidden() {
  _pvUpdateReadouts();
  var json = document.getElementById('new-project-sections');
  var checks = document.querySelectorAll('#section-toggle-row .section-toggle');
  var sections = [];
  for (var i = 0; i < checks.length; i++) {
    if (checks[i].checked) sections.push(checks[i].value);
  }
  if (json) json.value = JSON.stringify(sections);

  var layout = { anchor: 'center', block_width_pct: 80, numbered_scale: 1.6, pill_per_word: true };
  var active = document.querySelector('#new-project-anchor .anchor-btn[class*="bg-primary"]');
  if (active && active.getAttribute('data-anchor')) layout.anchor = active.getAttribute('data-anchor');
  var bw = document.getElementById('new-project-block-width');
  if (bw) layout.block_width_pct = parseInt(bw.value, 10);
  var ns = document.getElementById('new-project-numbered-scale');
  if (ns) layout.numbered_scale = parseFloat(ns.value);
  var pm = document.getElementById('new-project-pill-mode');
  if (pm) layout.pill_per_word = pm.checked;
  var wc = document.getElementById('new-project-watermark-corner');
  if (wc && wc.value) layout.watermark_corner = wc.value;
  var wsize = document.getElementById('new-project-watermark-size');
  if (wsize) layout.watermark_size_pct = parseInt(wsize.value, 10);
  var wop = document.getElementById('new-project-watermark-opacity');
  if (wop) layout.watermark_opacity = parseFloat(wop.value);
  var mvol = document.getElementById('new-project-music-volume');
  if (mvol) layout.music_volume = parseFloat(mvol.value);
  var mfade = document.getElementById('new-project-music-fade');
  if (mfade) layout.music_fade_seconds = parseFloat(mfade.value);
  var fout = document.getElementById('new-project-fade-out');
  if (fout) layout.fade_out_seconds = parseFloat(fout.value);
  var layoutJson = document.getElementById('new-project-layout-json');
  if (layoutJson) layoutJson.value = JSON.stringify(layout);

  var style = { chunk_size: 3 };
  var cs = document.getElementById('new-project-chunk-size');
  if (cs) style.chunk_size = parseInt(cs.value, 10);
  var csize = document.getElementById('new-project-caption-size');
  if (csize) style.caption_font_size = parseInt(csize.value, 10);
  var outline = document.getElementById('new-project-outline-width');
  if (outline) style.caption_outline_width = parseInt(outline.value, 10);
  var up = document.getElementById('new-project-uppercase');
  if (up) style.uppercase = up.checked;
  var scrim = document.getElementById('new-project-scrim');
  if (scrim) style.scrim_alpha = parseFloat(scrim.value);
  var styleJson = document.getElementById('new-project-style-json');
  if (!styleJson) {
    styleJson = document.createElement('input');
    styleJson.type = 'hidden';
    styleJson.id = 'new-project-style-json';
    styleJson.name = 'style';
    document.getElementById('composer-style-panel').appendChild(styleJson);
  }
  styleJson.value = JSON.stringify(style);

  var palFmt = document.getElementById('new-project-format');
  var defFmt = _preview_data.formats[(palFmt ? palFmt.value : 'narrated')] || {};
  var defPill = ((defFmt.palette || {}).highlight_colour) || _pvTokenHex('--primary', '0x7C5CFAFF');
  var defPillBg = ((defFmt.palette || {}).pill_bg_colour) || '0x000000C0';
  var palette = { highlight_colour: defPill, pill_bg_colour: defPillBg };
  var pc = document.getElementById('new-project-highlight-colour');
  if (pc) palette.highlight_colour = pc.value.replace('#', '0x') + 'FF';
  var pb = document.getElementById('new-project-pill-colour');
  if (pb) palette.pill_bg_colour = pb.value.replace('#', '0x') + 'FF';
  var paletteJson = document.getElementById('new-project-palette-json');
  if (!paletteJson) {
    paletteJson = document.createElement('input');
    paletteJson.type = 'hidden';
    paletteJson.id = 'new-project-palette-json';
    paletteJson.name = 'palette';
    document.getElementById('composer-style-panel').appendChild(paletteJson);
  }
  paletteJson.value = JSON.stringify(palette);

  var stages = { music: false, outro: true, watermark: false, background: true };
  var stageJson = document.getElementById('new-project-stages-json');
  if (stageJson) {
    var fmt = document.getElementById('new-project-format');
    var fmtName = fmt ? fmt.value : 'narrated';
    var info = _preview_data.formats[fmtName];
    var declared = stageJson.getAttribute('data-stages');
    if (declared) {
      try {
        var parsed = JSON.parse(declared);
        for (var k in stages) if (parsed[k] !== undefined) stages[k] = !!parsed[k];
      } catch (e) {}
      if (info && info.rank) stages.music = true;
    } else {
      stages.music = !!(info && info.rank);
    }
    var stageChecks = document.querySelectorAll('#new-project-stages .stage-toggle');
    for (var sj = 0; sj < stageChecks.length; sj++) {
      var sk = stageChecks[sj].getAttribute('data-stage');
      if (!sk || stages[sk] === undefined) continue;
      if (_pvTouchedStages[sk]) stages[sk] = stageChecks[sj].checked;
      else stageChecks[sj].checked = stages[sk];
    }
    stageJson.value = JSON.stringify(stages);
  }
  var motionJson = document.getElementById('new-project-background-motion-json');
  if (motionJson) {
    var motionBtn = document.querySelector('#new-project-motion .motion-btn[class*="bg-primary"]');
    motionJson.value = motionBtn ? motionBtn.getAttribute('data-motion') : '';
  }
  var emphasisJson = document.getElementById('new-project-emphasis-json');
  if (emphasisJson) {
    var emphasisBtn = document.querySelector('#new-project-emphasis .emphasis-btn[class*="bg-primary"]');
    emphasisJson.value = emphasisBtn ? emphasisBtn.getAttribute('data-emphasis') : '';
  }
  var lufs = document.getElementById('new-project-loudness');
  var lufsJson = document.getElementById('new-project-loudness-json');
  if (lufsJson && lufs && lufs.value !== '' && Math.abs(parseFloat(lufs.value) + 14) > 0.01) {
    lufsJson.value = lufs.value;
  } else if (lufsJson) {
    lufsJson.value = '';
  }
  var normalize = document.getElementById('new-project-audio-normalize');
  var normalizeJson = document.getElementById('new-project-audio-normalize-json');
  if (normalizeJson) normalizeJson.value = normalize && !normalize.checked ? 'false' : '';
  var holds = {};
  var holdHook = document.getElementById('new-project-hold-hook');
  if (holdHook && parseFloat(holdHook.value) > 0) holds.hook = parseFloat(holdHook.value);
  var msgPace = document.getElementById('new-project-message-pacing');
  var messageHold = msgPace ? parseFloat(msgPace.value) - 1.0 : 0;
  if (messageHold !== 0) holds.message = messageHold;
  var holdConcl = document.getElementById('new-project-hold-conclusion');
  if (holdConcl && parseFloat(holdConcl.value) > 0) holds.conclusion = parseFloat(holdConcl.value);
  var holdsJson = document.getElementById('new-project-section-holds-json');
  if (holdsJson) holdsJson.value = Object.keys(holds).length ? JSON.stringify(holds) : '';
  var accents = {};
  var stageKeys = {
    'new-project-stage-accent-hook': 'hook',
    'new-project-stage-accent-message': 'message',
    'new-project-stage-accent-metaphor': 'metaphor',
    'new-project-stage-accent-conclusion': 'conclusion'
  };
  for (var contId in stageKeys) {
    var active = document.querySelector('#' + contId + ' .accent-chip[class*="ring-primary"]');
    if (!active) continue;
    var accentColour = active.getAttribute('data-colour');
    if (accentColour) accents[stageKeys[contId]] = accentColour;
  }
  var accentsJson = document.getElementById('new-project-stage-accents-json');
  if (accentsJson) accentsJson.value = Object.keys(accents).length ? JSON.stringify(accents) : '';
  serializeResolvedSpec();
  _pvUpdateSummary();
  var structuredSpec = {};
  var specJson = document.getElementById('spec-json');
  if (specJson) {
    try { structuredSpec = JSON.parse(specJson.textContent); } catch (e) { structuredSpec = {}; }
  }
  _pvRenderStructuredSpec(structuredSpec);
}

function _pvClampToRange(value, range) {
  var clamped = value;
  var changed = false;
  if (typeof value === 'number' && range && range.length === 2 && range[1] >= range[0]) {
    if (value < range[0]) { clamped = range[0]; changed = true; }
    else if (value > range[1]) { clamped = range[1]; changed = true; }
  }
  return { value: clamped, changed: changed };
}

function _pvClampToast(message) {
  if (window.showToast) window.showToast(message);
}

function serializeResolvedSpec() {
  var spec = {};
  var fmt = document.getElementById('new-project-format');
  spec.format_name = fmt ? fmt.value : 'narrated';
  var dur = document.getElementById('new-project-duration');
  if (dur && dur.value !== '') spec.duration_seconds = parseFloat(dur.value);
  var pacing = document.getElementById('new-project-pacing');
  if (pacing) spec.pacing_wps = parseFloat(pacing.value);
  var fmtInfo = _preview_data.formats[spec.format_name] || _preview_data.formats.narrated;
  var clampedDur = _pvClampToRange(spec.duration_seconds, fmtInfo.duration_range);
  if (clampedDur.changed) {
    spec.duration_seconds = clampedDur.value;
    if (dur) dur.value = clampedDur.value;
    _pvClampToast('Duration clamped to ' + clampedDur.value + 's for ' + (fmtInfo.label || spec.format_name));
  }
  var clampedPace = _pvClampToRange(spec.pacing_wps, fmtInfo.pacing_wps_range);
  if (clampedPace.changed) {
    spec.pacing_wps = clampedPace.value;
    if (pacing) pacing.value = clampedPace.value;
    _pvClampToast('Pacing clamped to ' + clampedPace.value + ' wps for ' + (fmtInfo.label || spec.format_name));
  }
  var hookEl = document.getElementById('new-project-hook-text');
  if (hookEl && hookEl.value.trim() !== '') spec.hook_text = hookEl.value.trim();
  var sections = document.getElementById('new-project-sections');
  if (sections && sections.value) spec.sections = JSON.parse(sections.value);
  var style = document.getElementById('new-project-style-json');
  if (style && style.value) spec.style = JSON.parse(style.value);
  var palette = document.getElementById('new-project-palette-json');
  if (palette && palette.value) spec.palette = JSON.parse(palette.value);
  var layout = document.getElementById('new-project-layout-json');
  if (layout && layout.value) spec.layout = JSON.parse(layout.value);
  var stages = document.getElementById('new-project-stages-json');
  if (stages && stages.value) spec.stages = JSON.parse(stages.value);
  var motionSpec = document.getElementById('new-project-background-motion-json');
  if (motionSpec && motionSpec.value) spec.background_motion = motionSpec.value;
  var lufsSpec = document.getElementById('new-project-loudness-json');
  if (lufsSpec && lufsSpec.value !== '') spec.loudness_target_lufs = parseFloat(lufsSpec.value);
  var normSpec = document.getElementById('new-project-audio-normalize-json');
  if (normSpec && normSpec.value !== '') spec.audio_normalize = normSpec.value === 'true';
  var emphSpec = document.getElementById('new-project-emphasis-json');
  if (emphSpec && emphSpec.value) spec.emphasis_style = emphSpec.value;
  var holdsSpec = document.getElementById('new-project-section-holds-json');
  if (holdsSpec && holdsSpec.value) spec.section_holds = JSON.parse(holdsSpec.value);
  var accSpec = document.getElementById('new-project-stage-accents-json');
  if (accSpec && accSpec.value) spec.stage_accents = JSON.parse(accSpec.value);
  var out = document.getElementById('spec-json');
  if (out) out.textContent = JSON.stringify(spec, null, 2);
}

function _presetsRefresh(select) {
  fetch('/api/composer/presets')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var presets = data.presets || [];
      var selected = select.selectedOptions[0] ? select.selectedOptions[0].value : '';
      select.innerHTML = '';
      var chips = document.getElementById('preset-chips');
      if (chips) chips.innerHTML = '';
      presets.forEach(function(p) {
        var o = document.createElement('option');
        o.value = p.name;
        o.textContent = p.name;
        select.appendChild(o);
        if (!chips) return;
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'preset-chip px-2.5 py-1 rounded-full text-[10px] font-mono cursor-pointer transition-colors ' +
          (p.builtin ? 'bg-secondary/60 text-muted-foreground hover:bg-secondary'
                     : 'bg-secondary text-foreground hover:bg-primary/20');
        b.textContent = p.name;
        b.title = p.builtin ? 'Built-in starter preset' : 'Saved preset';
        b.setAttribute('data-preset-name', p.name);
        b.addEventListener('click', function(ev) { _presetsSelectChip(ev.currentTarget); });
        chips.appendChild(b);
      });
      if (selected) select.value = selected;
      _presetsMarkChip(selected);
    });
}

function _presetsMarkChip(name) {
  var chips = document.getElementById('preset-chips');
  if (!chips) return;
  chips.querySelectorAll('.preset-chip').forEach(function(b) {
    var on = b.getAttribute('data-preset-name') === name;
    b.classList.toggle('ring-2', on);
    b.classList.toggle('ring-primary', on);
  });
}

function _presetsSelectChip(btn) {
  var name = btn.getAttribute('data-preset-name');
  var select = document.getElementById('preset-select');
  if (select) select.value = name;
  _presetsMarkChip(name);
  applyPreset();
}

function _presetsSelected() {
  var select = document.getElementById('preset-select');
  if (!select || !select.selectedOptions.length) return '';
  return select.selectedOptions[0].value;
}

function _presetsSetValue(id, value) {
  if (value === undefined || value === null || value === '') return;
  var elNode = document.getElementById(id);
  if (elNode) elNode.value = value;
}

function _presetsApplySpec(spec) {
  _presetsSetValue('new-project-format', spec.format_name);
  _presetsSetValue('new-project-duration', spec.duration_seconds);
  _presetsSetValue('new-project-pacing', spec.pacing_wps);
  _presetsSetValue('new-project-hook-text', spec.hook_text);

  var style = spec.style || {};
  _presetsSetValue('new-project-chunk-size', style.chunk_size);
  _presetsSetValue('new-project-caption-size', style.caption_font_size);
  _presetsSetValue('new-project-outline-width', style.caption_outline_width);
  var up = document.getElementById('new-project-uppercase');
  if (up) up.checked = !!style.uppercase;
  _presetsSetValue('new-project-scrim', style.scrim_alpha);

  var palette = spec.palette || {};
  if (palette.highlight_colour) {
    var hc = document.getElementById('new-project-highlight-colour');
    if (hc) hc.value = '#' + String(palette.highlight_colour).replace('0x', '').substring(0, 6).toLowerCase();
  }
  if (palette.pill_bg_colour) {
    var pb = document.getElementById('new-project-pill-colour');
    if (pb) pb.value = '#' + String(palette.pill_bg_colour).replace('0x', '').substring(0, 6).toLowerCase();
  }

  var layout = spec.layout || {};
  if (layout.anchor) {
    var anchorBtn = document.querySelector('#new-project-anchor .anchor-btn[data-anchor="' + layout.anchor + '"]');
    if (anchorBtn) anchorBtn.click();
  }
  _presetsSetValue('new-project-block-width', layout.block_width_pct);
  _presetsSetValue('new-project-numbered-scale', layout.numbered_scale);
  var pm = document.getElementById('new-project-pill-mode');
  if (pm) pm.checked = layout.pill_per_word !== false;
  _presetsSetValue('new-project-watermark-corner', layout.watermark_corner);
  _presetsSetValue('new-project-watermark-size', layout.watermark_size_pct);
  _presetsSetValue('new-project-watermark-opacity', layout.watermark_opacity);
  _presetsSetValue('new-project-music-volume', layout.music_volume);
  _presetsSetValue('new-project-music-fade', layout.music_fade_seconds);
  _presetsSetValue('new-project-fade-out', layout.fade_out_seconds);

  var sections = document.getElementById('new-project-sections');
  if (spec.sections && sections) {
    sections.value = JSON.stringify(spec.sections);
    buildSectionToggles();
  }
  var stages = document.getElementById('new-project-stages-json');
  if (stages && spec.stages) {
    stages.setAttribute('data-stages', JSON.stringify(spec.stages));
    document.querySelectorAll('#new-project-stages .stage-toggle').forEach(function(cb) {
      var sk = cb.getAttribute('data-stage');
      if (sk && spec.stages[sk] !== undefined) cb.checked = !!spec.stages[sk];
    });
  }

  if (spec.background_motion) {
    var motBtn = document.querySelector(
      '#new-project-motion .motion-btn[data-motion="' + spec.background_motion + '"]'
    );
    if (motBtn) motBtn.click();
  }
  if (spec.emphasis_style) {
    var emphBtn = document.querySelector(
      '#new-project-emphasis .emphasis-btn[data-emphasis="' + spec.emphasis_style + '"]'
    );
    if (emphBtn) emphBtn.click();
  }
  _presetsSetValue('new-project-loudness', spec.loudness_target_lufs);
  var normalize = document.getElementById('new-project-audio-normalize');
  if (normalize) normalize.checked = spec.audio_normalize !== false;

  var holds = spec.section_holds || {};
  _presetsSetValue('new-project-hold-hook', holds.hook || 0);
  _presetsSetValue('new-project-message-pacing', (holds.message || 0) + 1.0);
  _presetsSetValue('new-project-hold-conclusion', holds.conclusion || 0);

  var accents = spec.stage_accents || {};
  var stageKeys = {
    'new-project-stage-accent-hook': 'hook',
    'new-project-stage-accent-message': 'message',
    'new-project-stage-accent-metaphor': 'metaphor',
    'new-project-stage-accent-conclusion': 'conclusion'
  };
  for (var contId in stageKeys) {
    var cont = document.getElementById(contId);
    if (!cont) continue;
    var colour = accents[stageKeys[contId]];
    var matched = null;
    var noneBtn = null;
    var btns = cont.querySelectorAll('.accent-chip');
    for (var bi = 0; bi < btns.length; bi++) {
      if (!btns[bi].getAttribute('data-accent')) { noneBtn = btns[bi]; continue; }
      if (btns[bi].getAttribute('data-colour') === colour) { matched = btns[bi]; break; }
    }
    if (matched) matched.click();
    else if (noneBtn) noneBtn.click();
  }

  syncComposerHidden();
  mirrorPreview();
}

function applyPreset() {
  var name = _presetsSelected();
  if (!name) return;
  fetch('/api/composer/presets')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var presets = data.presets || [];
      var preset = null;
      for (var i = 0; i < presets.length; i++) {
        if (presets[i].name === name) { preset = presets[i]; break; }
      }
      if (!preset || !preset.payload) {
        if (window.showToast) window.showToast('Preset not found', 'error');
        return;
      }
      _presetsApplySpec(preset.payload);
      if (window.showToast) window.showToast('Preset applied', 'success');
    });
}

function savePreset() {
  var name = window.prompt('Preset name', '');
  if (!name) return;
  syncComposerHidden();
  var specJson = document.getElementById('spec-json');
  var spec = {};
  if (specJson) {
    try { spec = JSON.parse(specJson.textContent); } catch (e) { spec = {}; }
  }
  fetch('/api/composer/presets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name, payload: spec })
  }).then(function(r) { return r.text(); })
    .then(function() {
      var select = document.getElementById('preset-select');
      if (select) _presetsRefresh(select);
      if (window.showToast) window.showToast('Preset saved', 'success');
    });
}

function deletePreset() {
  var name = _presetsSelected();
  if (!name) return;
  if (!window.confirm('Delete preset "' + name + '"?')) return;
  fetch('/api/composer/presets/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name })
  }).then(function(r) { return r.text(); })
    .then(function(text) {
      if (text && text.indexOf('builtin') >= 0) {
        if (window.showToast) window.showToast('Cannot delete builtin preset', 'error');
        return;
      }
      var select = document.getElementById('preset-select');
      if (select) _presetsRefresh(select);
      if (window.showToast) window.showToast('Preset deleted', 'success');
    });
}

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
