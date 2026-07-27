const fs = require('fs');
const path = require('path');
const SRC = path.join(__dirname, '..', '..', 'src', 'shorts_creator', 'ui', 'static', 'js', 'composer-preview.js');
const src = fs.readFileSync(SRC, 'utf8');

function makeEl(id, value) {
  const el = {
    id: id || '', _value: value === undefined || value === null ? '' : String(value), checked: false, type: '', name: '', disabled: false,
    style: {}, dataset: {}, attrs: {}, textContent: '',
    className: '', children: [], selectedOptions: [],
    offsetHeight: undefined,
    classList: {
      _s: new Set(),
      _apply(del, add) {
        const tokens = new Set((this._host.className || '').split(/\s+/).filter(Boolean));
        del.forEach(t => tokens.delete(t));
        add.forEach(t => tokens.add(t));
        this._host.className = Array.from(tokens).join(' ');
      },
      add(...c) { c.forEach(x => this._s.add(x)); this._apply([], c); },
      remove(...c) { c.forEach(x => this._s.delete(x)); this._apply(c, []); },
      toggle(c, on) { if (on === undefined) on = !this._s.has(c); on ? this._s.add(c) : this._s.delete(c); this._apply(on ? [] : [c], on ? [c] : []); return on; },
      contains(c) { return this._s.has(c); }
    },
    listeners: {},
    addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); },
    dispatch(type) { (this.listeners[type] || []).forEach(fn => fn({ type })); },
    appendChild(c) { this.children.push(c); },
    setAttribute(k, v) { this.attrs[k] = v; },
    getAttribute(k) { return this.attrs[k] !== undefined ? this.attrs[k] : null; },
    click() {
      if (this.getAttribute('data-accent')) this.classList.add('ring-primary');
      else this.classList.remove('ring-primary');
      this.dispatch('click');
    },
    querySelectorAll(sel) {
      if (sel === '.accent-chip') return this.children.filter(c => c.className.indexOf('accent-chip') >= 0);
      const needPvCap = sel === 'span.pv-cap';
      return this.children.filter(c => needPvCap ? (c.className.indexOf('pv-cap') >= 0) : false);
    }
  };
  el.classList._host = el;
  Object.defineProperty(el, 'value', {
    get() { return el._value; },
    set(v) { el._value = v === undefined || v === null ? '' : String(v); }
  });
  Object.defineProperty(el, 'innerHTML', {
    get() { return ''; },
    set(html) {
      el.children = [];
      const re = /<span class="([^"]+)">([^<]*)<\/span>/g;
      let m;
      while ((m = re.exec(html)) !== null) {
        const c = makeEl('', '');
        c.className = m[1];
        c.textContent = m[2];
        (c.className.match(/pv-(cap|pill|hook)\b/g) || []).forEach(cls => c.classList.add(cls));
        if (c.className.indexOf('pv-pill') >= 0) c.classList.add('pv-pill');
        el.children.push(c);
      }
    }
  });
  return el;
}

const els = {};
function reg(id, value) {
  const el = makeEl(id, value);
  els[id] = el;
  return el;
}
function findRecursive(node, id) {
  if (node.id === id) return node;
  for (const c of (node.children || [])) { const hit = findRecursive(c, id); if (hit) return hit; }
  return null;
}
function findByClass(root, cls) {
  const out = [];
  function walk(n) {
    if (n.className && n.className.split(/\s+/).indexOf(cls) >= 0) out.push(n);
    n.children.forEach(walk);
  }
  walk(root);
  return out;
}

// --- form widgets (defaults) ---
const WIDGET_DEFAULTS = {
  'new-project-title': '', 'new-project-focus': '',
  'new-project-format': 'narrated', 'new-project-duration': '30',
  'new-project-type': 'self_improvement',
  'new-project-pacing': '2.6', 'new-project-hook-text': '',
  'new-project-chunk-size': '3', 'new-project-highlight-colour': '#7c5cfa',
  'new-project-pill-colour': '#000000', 'new-project-caption-size': '56',
  'new-project-outline-width': '2', 'new-project-block-width': '80',
  'new-project-numbered-scale': '1.6', 'new-project-pill-mode': '',
  'new-project-uppercase': '', 'new-project-scrim': '0',
  'new-project-watermark-corner': '', 'new-project-watermark-size': '10',
  'new-project-watermark-opacity': '0.6', 'new-project-music-volume': '0.6',
  'new-project-music-fade': '2', 'new-project-fade-out': '1',
  'new-project-motion': '', 'new-project-emphasis': '',
  'new-project-loudness': '', 'new-project-audio-normalize': '',
  'new-project-hold-hook': '0', 'new-project-message-pacing': '1',
  'new-project-hold-conclusion': '0',
  'new-project-sections': '["hook","message","metaphor","conclusion"]',
  'new-project-style-json': '', 'new-project-palette-json': '',
  'new-project-layout-json': '', 'new-project-stages-json': '',
  'new-project-background-motion-json': '', 'new-project-loudness-json': '',
  'new-project-audio-normalize-json': '', 'new-project-section-holds-json': '',
  'new-project-stage-accents-json': '', 'new-project-outro-text': '',
};
Object.keys(WIDGET_DEFAULTS).forEach(id => reg(id, WIDGET_DEFAULTS[id]));
els['new-project-uppercase'].type = 'checkbox';
els['new-project-pill-mode'].type = 'checkbox';
els['new-project-audio-normalize'].type = 'checkbox';
els['new-project-type'].type = 'hidden';

// --- preview nodes ---
const previewIds = [
  'preview-hook-block', 'preview-caption', 'preview-caption-highlight',
  'preview-caption-plain', 'preview-duration-fill', 'preview-duration-bar',
  'preview-timeline-ticks', 'preview-topic-dot', 'preview-ranking-block',
  'preview-bg-layer', 'preview-outro', 'preview-mid-block',
  'preview-play-icon', 'preview-pause-icon', 'preview-play-btn',
  'preview-position-display',
  'duration-range-hint', 'composer-summary', 'spec-json', 'spec-structured',
  'composer-style-panel', 'composer-spec-panel',
];
previewIds.forEach(id => reg(id, ''));
// background video stub: spies for pause()/play() so the playback-controls
// wiring (pause freezes ticker AND video, play resumes both) is testable
const videoStub = makeEl('preview-bg-video', '');
videoStub.paused = true;
videoStub.playCalls = 0;
videoStub.pauseCalls = 0;
videoStub.currentTime = 0;
videoStub.play = function () { videoStub.paused = false; videoStub.playCalls++; };
videoStub.pause = function () { videoStub.paused = true; videoStub.pauseCalls++; };
els['preview-bg-video'] = videoStub;
// caption-style field: root wrapper with the server-rendered select nested
// inside (the live JS rebuilds this subtree on format switch, so lookups
// must traverse the field root rather than a flat registry entry)
reg('new-project-caption-field', '');
const capSel = makeEl('new-project-caption-style', 'highlight');
capSel.name = 'caption_style';
capSel.className = 'hidden';
const capOpt = makeEl('', 'Highlight (word-by-word)');
capOpt.value = 'highlight';
capSel.appendChild(capOpt);
els['new-project-caption-field'].appendChild(capSel);
// skeleton rows: narrated + topn, each with two skel-mid-label children
[['preview-skeleton-narrated', ['msg1', 'msg2']], ['preview-skeleton-topn', []]].forEach(([id, labels]) => {
  const s = reg(id, '');
  s.className = 'preview-skeleton';
  labels.forEach(l => { const n = makeEl('', l); n.className = 'skel-mid-label'; s.children.push(n); });
});
// timeline ticks (2 children required by _pvPositionTicks)
els['preview-timeline-ticks'].children.push(makeEl('t0', ''), makeEl('t1', ''));

// caption highlight seed spans (mirror the real static markup)
['First', 'practice,', 'kept', 'concrete'].forEach((w, i) => {
  const sp = makeEl('', w);
  sp.className = 'pv-cap' + (i === 1 ? ' pv-pill' : '');
  sp.classList.add('pv-cap');
  els['preview-caption-highlight'].children.push(sp);
});

// outro screen: text span (mirror the real static markup, gaining the binding id)
const outroSpan = makeEl('preview-outro-text', '');
outroSpan.textContent = 'Thanks for watching';
outroSpan.className = 'pv-font';
els['preview-outro'].children.push(outroSpan);

// section toggle row (content panel)
reg('section-toggle-row', '');
// stages toggle row (media panel): server renders four labeled checkboxes
// with data-stage keys, checked from the resolved stages (+ rank forcing)
reg('new-project-stages', '');
const stageDefault = { music: false, outro: true, watermark: false, background: true };
Object.keys(stageDefault).forEach(name => {
  const lb = makeEl('', '');
  lb.className = 'flex items-center gap-1.5 text-[11px] text-foreground';
  const cb = makeEl('', '');
  cb.type = 'checkbox';
  cb.className = 'accent-primary stage-toggle';
  cb.setAttribute('data-stage', name);
  cb.checked = stageDefault[name];
  lb.children.push(cb);
  els['new-project-stages'].children.push(lb);
});
// hidden asset fields used by summary
['bg_clip', 'music', 'outro_clip', 'watermark'].forEach(role => {
  reg(`new-project-asset-${role}-source`, 'assets');
  reg(`new-project-asset-${role}`, '');
  reg(`new-project-asset-${role}-url`, '');
});
reg('new-project-asset-font', '');

const root = Object.keys(els).map(k => els[k]);
const documentStub = {
  readyState: 'complete',
  getElementById(id) {
    if (els[id]) return els[id];
    for (const r of root) { const hit = findRecursive(r, id); if (hit) return hit; }
    return null;
  },
  querySelectorAll(sel) {
    if (sel === '.preview-skeleton') return root.filter(n => n.className.split(/\s+/).indexOf('preview-skeleton') >= 0);
    if (sel === '.accent-chip' || sel === '.motion-btn' || sel === '.emphasis-btn') return [];
    if (sel === '.section-toggle' || sel === '#section-toggle-row .section-toggle') {
      const row = els['section-toggle-row'];
      if (!row) return [];
      return row.children.flatMap(c => c.children.length ? c.children : [c]);
    }
    if (sel === '.stage-toggle' || sel === '#new-project-stages .stage-toggle') {
      const row = els['new-project-stages'];
      if (!row) return [];
      return row.children.flatMap(c => c.children.length ? c.children : [c]);
    }
    const m = sel.match(/^#preview-skeleton-narrated \.skel-mid-label$/);
    if (m) return els['preview-skeleton-narrated'].children;
    if (sel === '#preview-section-tabs button') return [];
    return [];
  },
  querySelector(sel) {
    const m = sel.match(/^#(new-project-stage-accent-.*) \.accent-chip\[class\*="ring-primary"\]$/);
    if (m) {
      const cont = els[m[1]];
      if (!cont) return null;
      return cont.children.find(c => c.className.indexOf('accent-chip') >= 0
        && c.className.indexOf('ring-primary') >= 0) || null;
    }
    return null;
  },
  createElement(tag) { return makeEl('', ''); },
  createTextNode(t) { return { textContent: t }; },
  addEventListener() {},
  documentElement: {},
};
const FORMAT_UI = {
  narrated: {
    options: [['highlight', 'Highlight (word-by-word)'], ['plain', 'Plain (static lines)']],
    help: 'Highlight tracks each spoken word; Plain keeps the whole line visible',
  },
  topn: {
    options: [['', 'Per-item screens'], ['list', 'List']],
    help: 'Per-item screens show one ranked item at a time; List shows the whole top n on one screen',
  },
};
global.document = documentStub;
global.window = {
  showToast(msg) { global.showToastCalls = (global.showToastCalls || []).concat(msg); },
  __FORMAT_UI_JSON__: FORMAT_UI,
};
global.fetch = () => Promise.resolve({ json: () => Promise.resolve({ presets: [] }) });
global.getComputedStyle = () => ({ getPropertyValue: () => '' });
global._preview_data = {
  formats: {
    narrated: {
      label: 'Narrated', duration_range: [30, 60], caption_styles: ['highlight', 'plain'],
      rank: false, layout: { anchor: 'center' },
      palette: { highlight_colour: '0x7C5CFAFF', pill_bg_colour: '0x000000C0' },
      skeleton: [
        { label: 'Hook', text: 'Understanding Procrastination Today' },
        { label: 'Message', text: 'Practice keeps progress concrete' },
        { label: 'Conclusion', text: 'Start small today' },
      ],
    },
    topn: {
      label: 'Top N', duration_range: [40, 75], caption_styles: [],
      rank: true, layout: { anchor: 'center' },
      palette: { highlight_colour: '0x22D3EEFF', pill_bg_colour: '0x123456C0' },
      skeleton: [
        { label: 'Hook', text: 'Top 5 habits' },
        { label: 'Item', num: '5', text: 'Morning routine, focus blocks' },
        { label: 'Item', num: '4', text: 'Deep work sessions' },
      ],
    },
  },
  topics: {
    self_improvement: { emoji: '💪', active_classes: ['bg-primary'], sections: ['hook', 'message', 'metaphor', 'conclusion'] },
    finance: { emoji: '📈', active_classes: ['bg-green-500'], sections: ['hook', 'message', 'metaphor', 'conclusion'] },
  },
};

// ---- load the real JS (init runs via readyState) ----
globalThis.setInterval = () => 1;
globalThis.clearInterval = () => {};
global.__PREVIEW_JSON__ = global._preview_data;
global.__PREVIEW_DATA_OBJ__ = global._preview_data;
global.__FORMAT_UI_JSON__ = FORMAT_UI;
eval(src);

// ---- assertion helpers ----
let passed = 0, failed = 0;
function assert(name, cond, detail) {
  if (cond) { passed++; console.log('  PASS  ' + name); }
  else { failed++; console.log('  FAIL  ' + name + (detail ? '  -- ' + detail : '')); }
}
const get = id => documentStub.getElementById(id);

// ---- 1. initial render from defaults ----
console.log('INIT (narrated/highlight/30s/topic self_improvement):');
assert('hook block shows narrated hook words',
  get('preview-hook-block').children.map(c => c.textContent).join(' ') === 'Understanding Procrastination Today');
assert('narrated skeleton visible', get('preview-skeleton-narrated').style.display === '');
assert('topn skeleton hidden', get('preview-skeleton-topn').style.display === 'none');
assert('highlight caption shown, plain hidden',
  get('preview-caption-highlight').style.display === '' && get('preview-caption-plain').style.display === 'none');
assert('duration hint text', get('duration-range-hint').textContent === 'Narrated renders 30–60s');
assert('ranking block hidden for narrated', get('preview-ranking-block').style.display === 'none');
assert('mid labels = message, metaphor',
  JSON.stringify(get('preview-skeleton-narrated').children.map(c => c.textContent)) === JSON.stringify(['message', 'metaphor']));

// ---- 2. duration fill + clamp (narrated, range 30-60) ----
console.log('DURATION:');
get('new-project-duration').value = '45';
get('new-project-duration').dispatch('input');
assert('fill at 50% for 45s (range 30-60)', get('preview-duration-fill').style.width === '50%', get('preview-duration-fill').style.width);
get('new-project-duration').value = '90';
get('new-project-duration').dispatch('input');
assert('out-of-range value clamped to 60 in the field', get('new-project-duration').value === '60', get('new-project-duration').value);
assert('fill clamps to 100% after clamp', get('preview-duration-fill').style.width === '100%');
assert('no warning after clamp (value in range)', get('duration-range-hint').style.color === '');
assert('clamp toast fired', (global.showToastCalls || []).join('|').indexOf('Duration clamped') === 0
  || (global.showToastCalls || []).some(s => s.indexOf('Duration clamped') >= 0));
get('new-project-duration').value = '60';
get('new-project-duration').dispatch('input');
assert('fill at 100% for top of range', get('preview-duration-fill').style.width === '100%');
get('new-project-duration').value = '30';
get('new-project-duration').dispatch('input');

// ---- 3. format switch -> topn (field rebuild: plain is invalid for topn, falls back to per-item) ----
console.log('FORMAT -> topn:');
get('new-project-caption-style').value = 'plain';
get('new-project-caption-style').dispatch('change');
get('new-project-format').value = 'topn';
get('new-project-format').dispatch('change');
assert('topn skeleton shown', get('preview-skeleton-topn').style.display === '');
assert('narrated skeleton hidden', get('preview-skeleton-narrated').style.display === 'none');
assert('hook block now topn hook', get('preview-hook-block').children.map(c => c.textContent).join(' ') === 'Top 5 habits');
assert('hint now Top N', get('duration-range-hint').textContent === 'Top N renders 40–75s');
assert('ranking block shown for topn', get('preview-ranking-block').style.display === '');
assert('caption field visible for topn', get('new-project-caption-field').style.display === '');
assert('caption field rebuilt to per-item/list options',
  get('new-project-caption-style').children.length === 2 &&
  get('new-project-caption-style').children.map(o => o.textContent).join('|') === 'Per-item screens|List');
assert('invalid plain falls back to per-item on topn', get('new-project-caption-style').value === '');
assert('caption line preview hidden for style-less topn', get('preview-caption').style.display === 'none');
get('new-project-duration').value = '45';
get('new-project-duration').dispatch('input');
assert('fill at 14% for 45s (topn range 40-75)', get('preview-duration-fill').style.width === '14%', get('preview-duration-fill').style.width);

// ---- 3b. list caption style preserved across unrelated re-renders ----
console.log('LIST STYLE -> narrated fallback:');
get('new-project-caption-style').value = 'list';
get('new-project-caption-style').dispatch('change');
get('new-project-format').value = 'narrated';
get('new-project-format').dispatch('change');
assert('list invalid for narrated, falls back to highlight',
  get('new-project-caption-style').value === 'highlight', get('new-project-caption-style').value);
assert('highlight preview restored after fallback', get('preview-caption-highlight').style.display === '');
assert('caption field rebuilt to highlight/plain options',
  get('new-project-caption-style').children.length === 2 &&
  get('new-project-caption-style').children.map(o => o.textContent).join('|') === 'Highlight (word-by-word)|Plain (static lines)');
get('new-project-format').value = 'topn';
get('new-project-format').dispatch('change');
assert('back to topn, per-item default', get('new-project-caption-style').value === '');
assert('ranking block back for topn', get('preview-ranking-block').style.display === '');

// ---- 4. caption style toggle (back to narrated) ----
console.log('CAPTION STYLE:');
get('new-project-format').value = 'narrated';
get('new-project-format').dispatch('change');
get('new-project-caption-style').value = 'highlight';
get('new-project-caption-style').dispatch('change');
assert('highlight restored', get('preview-caption-highlight').style.display === '');

// ---- 5. topic switch ----
console.log('TOPIC -> finance:');
get('new-project-type').value = 'finance';
get('new-project-type').dispatch('input');
assert('mid labels updated', JSON.stringify(get('preview-skeleton-narrated').children.map(c => c.textContent)) === JSON.stringify(['message', 'metaphor']));
assert('topic dot classes swapped', get('preview-topic-dot').classList.contains('bg-green-500'));

// ---- 6. pill colours: caption pill uses highlight, hook pills use pill bg at pipeline alpha ----
console.log('PILL COLOURS:');
function pillSpanOf() { return get('preview-caption-highlight').children.find(c => c.classList.contains('pv-pill')); }
const initCapPill = pillSpanOf().style.background;
assert('caption pill starts as palette highlight (#7c5cfa)',
  initCapPill === 'rgba(124, 92, 250, 1)', initCapPill);
const initHookBg = get('preview-hook-block').children[0].style.background;
assert('hook pills start dark with the pipeline 0.75 alpha',
  initHookBg === 'rgba(0, 0, 0, 0.75)', initHookBg);
get('new-project-highlight-colour').value = '#ff0000';
get('new-project-highlight-colour').dispatch('input');
assert('caption pill follows highlight colour', pillSpanOf().style.background === 'rgba(255, 0, 0, 1)', pillSpanOf().style.background);
get('new-project-pill-colour').value = '#ff0000';
get('new-project-pill-colour').dispatch('input');
const hookRed = get('preview-hook-block').children[0].style.background;
assert('hook pills follow pill colour at 0.75 alpha', hookRed === 'rgba(255, 0, 0, 0.75)', hookRed);
assert('caption pill unchanged by pill colour', pillSpanOf().style.background === 'rgba(255, 0, 0, 1)', pillSpanOf().style.background);
assert('plain span background untouched', get('preview-caption-plain').style.background === undefined);
get('new-project-highlight-colour').value = '#7c5cfa';
get('new-project-pill-colour').value = '#000000';
get('new-project-highlight-colour').dispatch('input');
get('new-project-pill-colour').dispatch('input');
assert('caption pill resets with highlight colour', pillSpanOf().style.background === 'rgba(124, 92, 250, 1)', pillSpanOf().style.background);

// ---- 7. caption size + outline ----
console.log('CAPTION SIZE / OUTLINE:');
const fsBefore = get('preview-caption-highlight').children[0].style.fontSize;
get('new-project-caption-size').value = '84';
get('new-project-caption-size').dispatch('input');
const fsAfter = get('preview-caption-highlight').children[0].style.fontSize;
assert('font size grows with knob', parseFloat(fsAfter) > parseFloat(fsBefore), fsBefore + ' -> ' + fsAfter);
const strokeBefore = get('preview-caption-highlight').children[0].style.WebkitTextStroke;
get('new-project-outline-width').value = '4';
get('new-project-outline-width').dispatch('input');
assert('outline stroke grows', get('preview-caption-highlight').children[0].style.WebkitTextStroke === '4px #000', strokeBefore + ' -> ' + get('preview-caption-highlight').children[0].style.WebkitTextStroke);

// ---- 7b. hook text mirrors live while typing ----
console.log('HOOK TEXT LIVE:');
get('new-project-hook-text').value = 'Quantum Breathing Mastered Today';
get('new-project-hook-text').dispatch('input');
const typedHook = get('preview-hook-block').children.map(c => c.textContent).join(' ');
assert('typed hook text mirrored into hook block',
  typedHook === 'Quantum Breathing Mastered Today', typedHook);
get('new-project-hook-text').value = '';
get('new-project-hook-text').dispatch('input');
const resetHook = get('preview-hook-block').children.map(c => c.textContent).join(' ');
assert('empty hook field falls back to skeleton hook',
  resetHook === 'Understanding Procrastination Today', resetHook);

// ---- 7c. outro text mirrors live ----
console.log('OUTRO TEXT LIVE:');
const outroTextEl = get('preview-outro-text');
assert('outro span carries the binding id', typeof outroTextEl !== 'undefined' && outroTextEl.textContent === 'Thanks for watching');
get('new-project-outro-text').value = 'See you next time';
get('new-project-outro-text').dispatch('input');
assert('typed outro text mirrored into outro screen', outroTextEl.textContent === 'See you next time', outroTextEl.textContent);
get('new-project-outro-text').value = '';
get('new-project-outro-text').dispatch('input');
assert('empty outro field falls back to default', outroTextEl.textContent === 'Thanks for watching', outroTextEl.textContent);

// ---- 7d. section toggles update the preview immediately ----
console.log('SECTION TOGGLE:');
function secCheck(name) {
  const row = get('section-toggle-row');
  for (const c of row.children) {
    const hit = c.children.find(x => x.value === name);
    if (hit) return hit;
  }
  return undefined;
}
assert('section toggle row has message/metaphor boxes',
  !!secCheck('message') && !!secCheck('metaphor'));
secCheck('message').checked = false;
secCheck('message').dispatch('change');
const midAfterUncheck = get('preview-skeleton-narrated').children.map(c => c.textContent);
assert('unchecked section removed from mirror mid pills',
  JSON.stringify(midAfterUncheck) === JSON.stringify(['metaphor', '']), JSON.stringify(midAfterUncheck));
secCheck('message').checked = true;
secCheck('message').dispatch('change');
const midAfterRecheck = get('preview-skeleton-narrated').children.map(c => c.textContent);
assert('rechecked section restored to mirror mid pills',
  JSON.stringify(midAfterRecheck) === JSON.stringify(['message', 'metaphor']), JSON.stringify(midAfterRecheck));

// ---- 7e. stage toggles wire into the submitted stages JSON ----
console.log('STAGE TOGGLE:');
function stageCheck(name) {
  for (const c of get('new-project-stages').children) {
    const hit = c.children.find(x => x.getAttribute('data-stage') === name);
    if (hit) return hit;
  }
  return undefined;
}
const stageKeys = ['music', 'outro', 'watermark', 'background'];
assert('four stage toggles rendered with data-stage keys',
  stageKeys.every(n => !!stageCheck(n)));
function stageJson() { return JSON.parse(get('new-project-stages-json').value); }
syncComposerHidden();
assert('untouched stage payload matches composer defaults',
  get('new-project-stages-json').value === '{"music":false,"outro":true,"watermark":false,"background":true}',
  get('new-project-stages-json').value);
stageCheck('music').checked = true;
stageCheck('music').dispatch('change');
assert('checked music lands in the submitted stage payload', stageJson().music === true, get('new-project-stages-json').value);
stageCheck('music').checked = false;
stageCheck('music').dispatch('change');
assert('unchecked music restored to default payload', stageJson().music === false, get('new-project-stages-json').value);
stageCheck('outro').checked = false;
stageCheck('outro').dispatch('change');
assert('unchecked outro lands in the submitted stage payload', stageJson().outro === false, get('new-project-stages-json').value);
stageCheck('outro').checked = true;
stageCheck('outro').dispatch('change');

// ---- 7f. preset apply sets the stage checkbox states ----
console.log('STAGE TOGGLE PRESET:');
_presetsApplySpec({ stages: { music: true, outro: false, watermark: true, background: false } });
assert('preset apply checks music/watermark, unchecks outro/background',
  stageCheck('music').checked === true && stageCheck('watermark').checked === true
    && stageCheck('outro').checked === false && stageCheck('background').checked === false);
assert('preset stage payload serialized after apply',
  JSON.stringify(stageJson()) === '{"music":true,"outro":false,"watermark":true,"background":false}',
  get('new-project-stages-json').value);

// ---- 7g. rank forcing is a default; a user toggle beats it ----
console.log('STAGE TOGGLE RANK:');
// mirror the settings page: server declared the profile stages (music:false)
// but rendered the toggles with the rank forcing applied (music checked)
get('new-project-stages-json').setAttribute('data-stages', '{"music":false,"outro":true,"watermark":false,"background":true}');
stageCheck('music').checked = true;
stageCheck('outro').checked = true;
stageCheck('watermark').checked = false;
stageCheck('background').checked = true;
get('new-project-format').value = 'topn';
get('new-project-format').dispatch('change');
assert('declared stage payload + rank forcing serialize music true',
  stageJson().music === true, get('new-project-stages-json').value);
stageCheck('music').checked = false;
stageCheck('music').dispatch('change');
assert('user-unchecked music beats the rank forcing',
  stageJson().music === false, get('new-project-stages-json').value);
stageCheck('music').checked = true;
stageCheck('music').dispatch('change');
delete els['new-project-stages-json'].attrs['data-stages'];
Object.keys(stageDefault).forEach(name => { stageCheck(name).checked = stageDefault[name]; });
get('new-project-format').value = 'narrated';
get('new-project-format').dispatch('change');
assert('back to narrated, payload returns to defaults',
  get('new-project-stages-json').value === '{"music":false,"outro":true,"watermark":false,"background":true}',
  get('new-project-stages-json').value);

// ---- 7h. untouched stage toggles track format changes (no spurious override) ----
console.log('STAGE TOGGLE FORMAT SWITCH (untouched):');
// harness cold-start: no stage has been toggled by the user in this page life
if (typeof _pvTouchedStages !== 'undefined') Object.keys(_pvTouchedStages).forEach(k => delete _pvTouchedStages[k]);
// page rendered for a non-rank format: defaults, music unchecked
stageCheck('music').checked = false;
stageCheck('outro').checked = true;
stageCheck('watermark').checked = false;
stageCheck('background').checked = true;
get('new-project-format').value = 'narrated';
get('new-project-format').dispatch('change');
get('new-project-format').value = 'topn';
get('new-project-format').dispatch('change');
assert('narrated -> topn with no touch: payload music stays true (neutral)',
  stageJson().music === true, get('new-project-stages-json').value);
assert('narrated -> topn with no touch: music toggle re-synced to checked',
  stageCheck('music').checked === true);
// mirror: page rendered on rank (declared music:false, toggle forced checked)
get('new-project-stages-json').setAttribute('data-stages', '{"music":false,"outro":true,"watermark":false,"background":true}');
stageCheck('music').checked = true;
get('new-project-format').dispatch('change');
assert('rank page with no touch: payload music stays true',
  stageJson().music === true, get('new-project-stages-json').value);
get('new-project-format').value = 'narrated';
get('new-project-format').dispatch('change');
assert('topn -> narrated with no touch: payload music returns to declared false (no spurious true)',
  stageJson().music === false, get('new-project-stages-json').value);
assert('topn -> narrated with no touch: music toggle re-synced to unchecked',
  stageCheck('music').checked === false);
delete els['new-project-stages-json'].attrs['data-stages'];
Object.keys(stageDefault).forEach(name => { stageCheck(name).checked = stageDefault[name]; });
get('new-project-format').value = 'narrated';
get('new-project-format').dispatch('change');

// ---- 8. block width -> hook font ----
console.log('BLOCK WIDTH:');
const hookBefore = get('preview-hook-block').children.map(c => parseFloat(c.style.fontSize));
get('new-project-block-width').value = '60';
get('new-project-block-width').dispatch('input');
const hookAfter = get('preview-hook-block').children.map(c => parseFloat(c.style.fontSize));
assert('hook font shrinks with narrower block', hookAfter[0] < hookBefore[0], hookBefore[0] + ' -> ' + hookAfter[0]);

// ---- 9. numbered scale (topn) ----
console.log('NUMBERED SCALE:');
get('new-project-format').value = 'topn';
get('new-project-format').dispatch('change');
const numBefore = parseFloat(get('preview-ranking-block').children[0].style.fontSize);
get('new-project-numbered-scale').value = '2.0';
get('new-project-numbered-scale').dispatch('input');
const numAfter = parseFloat(get('preview-ranking-block').children[0].style.fontSize);
assert('ranking number scales', numAfter > numBefore, numBefore + ' -> ' + numAfter);

// ---- 9b. list caption style (topn full list) ----
console.log('LIST STYLE (topn):');
get('new-project-caption-style').value = 'list';
get('new-project-caption-style').dispatch('change');
const listRows = get('preview-ranking-block').children.map(c => c.textContent);
assert('full list rows rendered',
  JSON.stringify(listRows) === JSON.stringify(['5. Morning routine focus blocks', '4. Deep work sessions']),
  JSON.stringify(listRows));
get('new-project-caption-style').value = '';
get('new-project-caption-style').dispatch('change');
const itemRows = get('preview-ranking-block').children.map(c => c.textContent);
assert('per-item screen restored on plain value',
  itemRows[0] === '5' && itemRows.length === 5,
  JSON.stringify(itemRows));

// ---- 10. renderer-only knobs do NOT disturb the phone preview ----
console.log('NON-VISUAL KNOBS (expected untouched):');
const hookSnapshot = get('preview-hook-block').children.map(c => c.textContent + c.style.fontSize).join('|');
get('new-project-chunk-size').value = '6';
get('new-project-chunk-size').dispatch('input');
get('new-project-uppercase').checked = true;
get('new-project-uppercase').dispatch('change');
get('new-project-motion').value = 'zoom';
get('new-project-motion').dispatch('input');
get('new-project-hold-hook').value = '1.5';
get('new-project-hold-hook').dispatch('input');
get('new-project-title').value = 'Untitled draft';
get('new-project-title').dispatch('input');
get('new-project-focus').value = 'drafting';
get('new-project-focus').dispatch('input');
assert('preview stable under renderer-only knobs',
  get('preview-hook-block').children.map(c => c.textContent + c.style.fontSize).join('|') === hookSnapshot);

// ---- 11. stage-accent key space: section names end-to-end ----
console.log('STAGE ACCENT KEY SPACE:');
function accentChip(accentName, colour, active) {
  const chip = makeEl('', '');
  chip.className = 'accent-chip w-7 h-7 rounded-full cursor-pointer transition-colors'
    + (accentName ? '' : ' bg-secondary') + (active ? ' ring-primary' : ' ring-border');
  chip.setAttribute('data-accent', accentName);
  chip.setAttribute('data-colour', colour);
  if (!accentName) chip.textContent = '\u2014';
  return chip;
}
const accentContainers = ['hook', 'message', 'metaphor', 'conclusion'].map(s => {
  const cont = reg('new-project-stage-accent-' + s, '');
  cont.appendChild(accentChip(null, null, false));
  [['violet', '0x7C5CFAFF'], ['cyan', '0x22D3EEFF'], ['emerald', '0x34D399FF'], ['rose', '0xFB7185FF']].forEach(
    ([name, colour]) => cont.appendChild(accentChip(name, colour, false)));
  return cont;
});
function activeAccentJson() {
  syncComposerHidden();
  return get('new-project-stage-accents-json').value;
}
assert('no accent selected serializes empty json', activeAccentJson() === '', activeAccentJson());
_presetsApplySpec({ stage_accents: { conclusion: '0xFB7185FF' } });
assert('preset apply selects the section-keyed accent chip',
  get('new-project-stage-accent-conclusion').children.find(c => c.getAttribute('data-colour') === '0xFB7185FF')
    .classList.contains('ring-primary'));
assert('preset apply re-serializes section-keyed accents', activeAccentJson() === '{"conclusion":"0xFB7185FF"}', activeAccentJson());
const msgCyan = get('new-project-stage-accent-message').children.find(c => c.getAttribute('data-accent') === 'cyan');
msgCyan.classList.add('ring-primary');
assert('selected chip serializes under its section name', activeAccentJson() === '{"message":"0x22D3EEFF","conclusion":"0xFB7185FF"}', activeAccentJson());
accentContainers.forEach(cont => cont.children.forEach(c => c.classList.remove('ring-primary')));
assert('clearing chips empties the accent payload', activeAccentJson() === '', activeAccentJson());

// ---- 12. knob reset: data-builtin restores the built-in default ----
console.log('KNOB RESET (data-builtin):');
// mirror the settings page: resolved (data-default) + builtin-tier values
els['new-project-hold-hook'].setAttribute('data-default', '0.4');
els['new-project-hold-hook'].setAttribute('data-builtin', '0');
els['new-project-message-pacing'].setAttribute('data-default', '2.5');
els['new-project-message-pacing'].setAttribute('data-builtin', '1');
els['new-project-hold-conclusion'].setAttribute('data-default', '0.3');
els['new-project-hold-conclusion'].setAttribute('data-builtin', '0');
get('new-project-hold-hook').value = '0.4';
get('new-project-message-pacing').value = '2.5';
get('new-project-hold-conclusion').value = '0.3';
syncComposerHidden();
assert('knob state serializes all three holds',
  get('new-project-section-holds-json').value === '{"hook":0.4,"message":1.5,"conclusion":0.3}',
  get('new-project-section-holds-json').value);
resetComposerKnob('new-project-message-pacing');
assert('reset moves message pacing to data_builtin', get('new-project-message-pacing').value === '1',
  get('new-project-message-pacing').value);
assert('reset drops the reset sub-key, preserving the others',
  get('new-project-section-holds-json').value === '{"hook":0.4,"conclusion":0.3}',
  get('new-project-section-holds-json').value);
resetComposerKnob('new-project-hold-hook');
resetComposerKnob('new-project-hold-conclusion');
assert('fully reset knobs serialize empty section holds',
  get('new-project-section-holds-json').value === '', get('new-project-section-holds-json').value);
assert('reset restored hook to data_builtin', get('new-project-hold-hook').value === '0');
assert('reset restored conclusion to data_builtin', get('new-project-hold-conclusion').value === '0');

// fallback: knob with only data-default (create page / non-pacing knobs)
els['new-project-message-pacing'].setAttribute('data-default', '1');
delete els['new-project-message-pacing'].attrs['data-builtin'];
get('new-project-message-pacing').value = '2.5';
syncComposerHidden();
assert('pre-fallback state serializes message hold',
  get('new-project-section-holds-json').value === '{"message":1.5}',
  get('new-project-section-holds-json').value);
resetComposerKnob('new-project-message-pacing');
assert('fallback reset restores data_default', get('new-project-message-pacing').value === '1',
  get('new-project-message-pacing').value);
assert('fallback reset still reserializes the payload',
  get('new-project-section-holds-json').value === '', get('new-project-section-holds-json').value);

// ---- 13. F2: the emitted palette default follows the SELECTED format ----
console.log('F2 PALETTE DEFAULT (selected format):');
// exercise the fallback path: drop the colour widgets so the format palette is used
els['new-project-highlight-colour'].id = '';
els['new-project-pill-colour'].id = '';
delete els['new-project-highlight-colour'];
delete els['new-project-pill-colour'];
get('new-project-format').value = 'topn';
syncComposerHidden();
const palJsonTopn = get('new-project-palette-json').value;
assert('palette default uses the selected (topn) palette',
  palJsonTopn.indexOf('0x22D3EEFF') >= 0 && palJsonTopn.indexOf('0x123456C0') >= 0, palJsonTopn);
assert('palette default dropped the narrated palette entry',
  palJsonTopn.indexOf('0x7C5CFAFF') < 0 && palJsonTopn.indexOf('0x000000C0') < 0, palJsonTopn);
get('new-project-format').value = 'narrated';
syncComposerHidden();
const palJsonNarr = get('new-project-palette-json').value;
assert('palette default follows narrated when selected again',
  palJsonNarr.indexOf('0x7C5CFAFF') >= 0 && palJsonNarr.indexOf('0x000000C0') >= 0, palJsonNarr);

console.log('\n' + passed + ' passed, ' + failed + ' failed');

// ---- 14. playback controls: pause/resume syncs the ticker AND the video ----
console.log('PLAYBACK CONTROLS (pause/resume + position readout):');
get('new-project-duration').value = '30';
_pvProgress = 0.25;
get('preview-position-display').textContent = '';
assert('readout never hidden (no display toggling)', get('preview-position-display').style.display !== 'none', get('preview-position-display').style.display);
togglePreviewPlay();
assert('play keeps saved position (no reset)', _pvProgress === 0.25, _pvProgress);
assert('play resumes the background video', videoStub.paused === false && videoStub.playCalls === 1, videoStub.paused);
assert('readout shows the playing position', get('preview-position-display').textContent === '0:07 / 0:30', get('preview-position-display').textContent);
togglePreviewPlay();
assert('pause freezes the ticker position', _pvProgress === 0.25, _pvProgress);
assert('pause pauses the background video', videoStub.paused === true && videoStub.pauseCalls === 1, videoStub.paused);
_pvTick();
assert('tick while paused does not advance progress', _pvProgress === 0.25, _pvProgress);
togglePreviewPlay();
_pvTick();
assert('resume advances from the saved position', _pvProgress > 0.25 && _pvProgress < 1, _pvProgress);
togglePreviewPlay();

process.exit(passed && !failed ? 0 : 1);
