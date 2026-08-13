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
