// build_lib.jsx — helpers for building graphics natively in After Effects (layers, keyframes, shapes, text, effects)
// Easing families, each measured off a hand-made reference project:
//   lin   : linear keys (fast pops, 2-frame opacity cuts)           -> ref: 6612/6612 16.667
//   s66   : bezier 66 / 66 influence (smooth in-out)               -> ref: Opacity / Scale 66,66
//   s33   : bezier 33 / 33
//   out   : out 33.333 -> in 82 (long decelerate)                  -> ref: logos / title slide
//   expo  : out ~0 -> in 100 (snap start, very long settle)        -> ref: Null position/scale
//   card  : 60 / 60 (card unfold)                                  -> ref: Scale Y 0 -> 163
//   trim  : linear out -> in 50 (trim-path draw-on)                -> ref: Trim Paths
var FPS = 30;
function fr(t) { return Math.round(t * FPS) / FPS; }
function TG(l) { return l.property("ADBE Transform Group"); }
function P(l) { return TG(l).property("ADBE Position"); }
function S(l) { return TG(l).property("ADBE Scale"); }
function O(l) { return TG(l).property("ADBE Opacity"); }
function A(l) { return TG(l).property("ADBE Anchor Point"); }
function R(l) { return TG(l).property("ADBE Rotate Z"); }
function col(c) { if (c.length === 3) { return [c[0], c[1], c[2], 1]; } return c; }

function easeDims(p) {
  var vt = p.propertyValueType;
  if (vt === PropertyValueType.ThreeD) { return 3; }
  if (vt === PropertyValueType.TwoD) { return 2; }
  return 1;
}
function setEase(p, k, inInf, outInf) {
  var n = easeDims(p), a = [], b = [];
  if (inInf < 0.1) { inInf = 0.1; }
  if (outInf < 0.1) { outInf = 0.1; }
  for (var i = 0; i < n; i++) { a.push(new KeyframeEase(0, inInf)); b.push(new KeyframeEase(0, outInf)); }
  p.setTemporalEaseAtKey(k, a, b);
}
function isSpatial(p) {
  var vt = p.propertyValueType;
  if (vt === PropertyValueType.TwoD_SPATIAL) { return true; }
  if (vt === PropertyValueType.ThreeD_SPATIAL) { return true; }
  return false;
}
// K(prop, [[t,v],...], mode) — add keys then shape them with one of the reference ease families
function K(p, arr, mode) {
  var idx = [], i, k;
  for (i = 0; i < arr.length; i++) { idx.push(p.addKey(fr(arr[i][0]))); p.setValueAtKey(idx[i], arr[i][1]); }
  // indices can shift when keys are added out of order; re-resolve by time
  for (i = 0; i < arr.length; i++) { idx[i] = p.nearestKeyIndex(fr(arr[i][0])); }
  for (i = 0; i < idx.length; i++) {
    k = idx[i];
    var first = (i === 0), last = (i === idx.length - 1);
    if (isSpatial(p)) {
      var z = (p.propertyValueType === PropertyValueType.ThreeD_SPATIAL) ? [0, 0, 0] : [0, 0];
      try { p.setSpatialTangentsAtKey(k, z, z); } catch (e1) {}
    }
    if (mode === "lin") { p.setInterpolationTypeAtKey(k, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR); }
    else if (mode === "hold") { p.setInterpolationTypeAtKey(k, KeyframeInterpolationType.HOLD, KeyframeInterpolationType.HOLD); }
    else if (mode === "s66") { setEase(p, k, 66, 66); }
    else if (mode === "s33") { setEase(p, k, 33.333, 33.333); }
    else if (mode === "card") { setEase(p, k, 60, 60); }
    else if (mode === "out") { setEase(p, k, first ? 16.667 : 82, last ? 16.667 : 33.333); }
    else if (mode === "expo") { setEase(p, k, first ? 16.667 : 100, last ? 16.667 : 0.1); }
    else if (mode === "trim") {
      if (first) { p.setInterpolationTypeAtKey(k, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR); }
      else { setEase(p, k, 50, 16.667); }
    }
  }
  return idx;
}
function holdAfter(p, t) { var k = p.nearestKeyIndex(fr(t)); p.setInterpolationTypeAtKey(k, p.keyInInterpolationType(k), KeyframeInterpolationType.HOLD); }
function holdKey(p, t, v) { var k = p.addKey(fr(t)); p.setValueAtKey(k, v); k = p.nearestKeyIndex(fr(t)); p.setInterpolationTypeAtKey(k, KeyframeInterpolationType.HOLD, KeyframeInterpolationType.HOLD); }

// overshoot — a bounce expression (amp/freq/decay exposed)
function overshoot(p, amp, freq, decay) {
  p.expression = "amp = " + amp + ";\nfreq = " + freq + ";\ndecay = " + decay + ";\nn = 0;\ntime_max = 3;\nif (numKeys > 0) {\n    n = nearestKey(time).index;\n    if (key(n).time > time) {\n        n--;\n    }\n}\nif (n == 0) {\n    t = 0;\n} else {\n    t = time - key(n).time;\n}\nif (n > 0 && t < time_max) {\n    v = velocityAtTime(key(n).time - thisComp.frameDuration / 10);\n    value + v * amp * Math.sin(freq * t * 2 * Math.PI) / Math.exp(decay * t);\n} else {\n    value;\n}";
}
// pop: linear scale 0 -> 100 in 7 frames + overshoot (ref: Shape Layer scale 0 -> 100, 12/12, BOUNCr)
function pop(l, t, sc) {
  if (sc === undefined) { sc = 100; }
  K(S(l), [[t, [0, 0, 100]], [t + 7 / FPS, [sc, sc, 100]]], "lin");
  overshoot(S(l), 0.035, 2.4, 6);
}
function fadeIn(l, t, d) { if (d === undefined) { d = 2 / FPS; } K(O(l), [[t, 0], [t + d, 100]], "lin"); }
function slideIn(l, t, dx, dy, d) {
  if (d === undefined) { d = 12 / FPS; }
  var p = P(l).value;
  K(P(l), [[t, [p[0] + dx, p[1] + dy]], [t + d, [p[0], p[1]]]], "out");
  K(O(l), [[t, 0], [t + 5 / FPS, 100]], "lin");
}
function span(l, a, b) { l.inPoint = fr(a); l.outPoint = fr(b); }

// ---------- shapes
function vg(l) { return l.property("ADBE Root Vectors Group"); }
function addGroup(l, name) { var g = vg(l).addProperty("ADBE Vector Group"); g.name = name; return g; }
function paint(g, fill, stroke, sw) {
  var c = g.property("ADBE Vectors Group");
  if (stroke) {
    var s = c.addProperty("ADBE Vector Graphic - Stroke");
    s.property("ADBE Vector Stroke Color").setValue(col(stroke));
    s.property("ADBE Vector Stroke Width").setValue(sw);
    s.property("ADBE Vector Stroke Line Cap").setValue(2);
    s.property("ADBE Vector Stroke Line Join").setValue(2);
  }
  if (fill) {
    var f = c.addProperty("ADBE Vector Graphic - Fill");
    f.property("ADBE Vector Fill Color").setValue(col(fill));
  }
}
function rectG(l, name, w, h, round, pos, fill, stroke, sw) {
  var g = addGroup(l, name), c = g.property("ADBE Vectors Group");
  var r = c.addProperty("ADBE Vector Shape - Rect");
  r.property("ADBE Vector Rect Size").setValue([w, h]);
  r.property("ADBE Vector Rect Roundness").setValue(round);
  if (pos) { r.property("ADBE Vector Rect Position").setValue(pos); }
  paint(g, fill, stroke, sw);
  return g;
}
function ellG(l, name, w, h, pos, fill, stroke, sw) {
  var g = addGroup(l, name), c = g.property("ADBE Vectors Group");
  var r = c.addProperty("ADBE Vector Shape - Ellipse");
  r.property("ADBE Vector Ellipse Size").setValue([w, h]);
  if (pos) { r.property("ADBE Vector Ellipse Position").setValue(pos); }
  paint(g, fill, stroke, sw);
  return g;
}
function pathG(l, name, verts, closed, fill, stroke, sw) {
  var g = addGroup(l, name), c = g.property("ADBE Vectors Group");
  var pth = c.addProperty("ADBE Vector Shape - Group");
  var sh = new Shape(); sh.vertices = verts; sh.closed = closed;
  pth.property("ADBE Vector Shape").setValue(sh);
  paint(g, fill, stroke, sw);
  return g;
}
function rectPath(g) { return g.property("ADBE Vectors Group").property("ADBE Vector Shape - Rect"); }
function addTrim(g) { return g.property("ADBE Vectors Group").addProperty("ADBE Vector Filter - Trim"); }
function shapeLayer(comp, name, x, y) { var l = comp.layers.addShape(); l.name = name; P(l).setValue([x, y]); return l; }

// ---------- text
function textLayer(comp, name, str, font, size, color, x, y, tracking, just) {
  var l = comp.layers.addText(str); l.name = name;
  var sp = l.property("ADBE Text Properties").property("ADBE Text Document");
  var d = sp.value;
  d.resetCharStyle();
  d.font = font; d.fontSize = size; d.applyFill = true; d.fillColor = [color[0], color[1], color[2]]; d.applyStroke = false;
  d.tracking = (tracking === undefined) ? -20 : tracking;
  if (just === "left") { d.justification = ParagraphJustification.LEFT_JUSTIFY; }
  else if (just === "right") { d.justification = ParagraphJustification.RIGHT_JUSTIFY; }
  else { d.justification = ParagraphJustification.CENTER_JUSTIFY; }
  sp.setValue(d);
  var r = l.sourceRectAtTime(0, false);
  if (just === "left") { A(l).setValue([r.left, r.top + r.height / 2]); }
  else if (just === "right") { A(l).setValue([r.left + r.width, r.top + r.height / 2]); }
  else { A(l).setValue([r.left + r.width / 2, r.top + r.height / 2]); }
  P(l).setValue([x, y]);
  return l;
}
// word-by-word slide + fade (ref: Animator 1 — Position [100,0], Opacity 0, Range Selector Offset -100 -> 100, Based On Words, Ramp Up)
function wordsIn(l, t, d, dx) {
  if (dx === undefined) { dx = 100; }
  var an = l.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator");
  var pr = an.property("ADBE Text Animator Properties");
  pr.addProperty("ADBE Text Position 3D").setValue([dx, 0, 0]);
  pr.addProperty("ADBE Text Opacity").setValue(0);
  var sel = an.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
  var adv = sel.property("ADBE Text Range Advanced");
  try { adv.property("ADBE Text Range Type2").setValue(3); } catch (e1) {}
  try { adv.property("ADBE Text Range Shape").setValue(2); } catch (e2) {}
  try { adv.property("ADBE Text Levels Max Ease").setValue(-50); } catch (e3) {}
  try { adv.property("ADBE Text Levels Min Ease").setValue(100); } catch (e4) {}
  K(sel.property("ADBE Text Percent Offset"), [[t, -100], [t + d, 100]], "lin");
}

// ---------- effects
function fx(l, mn) { return l.property("ADBE Effect Parade").addProperty(mn); }
// neon glow: two stacked native Glows (tight core + wide bloom) standing in for Deep Glow 2 (not loadable in this AE build)
function glow(l, radius, intensity) {
  var g1 = fx(l, "ADBE Glo2"); g1.name = "Glow core";
  g1.property("ADBE Glo2-0002").setValue(25.5 * 2); // threshold 20 %
  g1.property("ADBE Glo2-0003").setValue(radius * 0.35);
  g1.property("ADBE Glo2-0004").setValue(intensity);
  var g2 = fx(l, "ADBE Glo2"); g2.name = "Glow bloom";
  g2.property("ADBE Glo2-0002").setValue(25.5 * 2);
  g2.property("ADBE Glo2-0003").setValue(radius);
  g2.property("ADBE Glo2-0004").setValue(intensity * 0.7);
  return [g1, g2];
}
function blur(l, r) { var b = fx(l, "ADBE Box Blur2"); b.property("ADBE Box Blur2-0001").setValue(r); try { b.property("ADBE Box Blur2-0002").setValue(3); } catch (e) {} return b; }
function matte(l, m) { l.setTrackMatte(m, TrackMatteType.ALPHA); }
