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
