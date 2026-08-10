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
