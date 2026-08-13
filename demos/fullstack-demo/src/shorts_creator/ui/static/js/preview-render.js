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
