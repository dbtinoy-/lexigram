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
