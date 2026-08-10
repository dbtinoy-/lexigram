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
