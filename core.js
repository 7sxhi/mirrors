// 折り紙盤の規則（fold_rules.py と同じ。変えるときは両方を直す）
// マスは 色*100+数（色 1=赤 2=青 3=黄）、0 は空き。
// cscript（JScript）でも動くように、古い書き方（var・for）だけで書いてある。
var FoldCore = (function () {
  // 2マスの重なり。同じ色は足し算、違う色は大きいほうが差だけ残る（同じ数なら消える）
  function ov(a, b) {
    if (a === 0) return b;
    if (b === 0) return a;
    var ca = Math.floor(a / 100), va = a % 100, cb = Math.floor(b / 100), vb = b % 100;
    if (ca === cb) return ca * 100 + Math.min(va + vb, 99);
    if (va === vb) return 0;
    return va > vb ? ca * 100 + (va - vb) : cb * 100 + (vb - va);
  }

  // 盤 b = {w, h, cells, ox, oy}（ox, oy は最初の紙の中での左上の位置）
  // move = ['V', k]（左から k 列目と k+1 列目の間の縦線）か ['H', k]（上から k 行目の下の横線）
  // 短い側が鏡写しに裏返って長い側に重なる。同じ長さなら左を右へ、上を下へ。
  // 返り値の flip は裏返る側（'L' 'R' 'T' 'B'）
  function fold(b, move) {
    var t = move[0], k = move[1], w = b.w, h = b.h, c = b.cells, out = [];
    var x, y, d, nw, nh, a, bb;
    if (t === 'V') {
      var L = k, R = w - k;
      if (R >= L) {
        nw = R;
        for (y = 0; y < h; y++) {
          for (d = 0; d < nw; d++) {
            a = c[y * w + k + d];
            bb = d < L ? c[y * w + k - 1 - d] : 0;
            out[y * nw + d] = ov(a, bb);
          }
        }
        return { w: nw, h: h, cells: out, ox: b.ox + k, oy: b.oy, flip: 'L' };
      }
      nw = L;
      for (y = 0; y < h; y++) {
        for (d = 0; d < nw; d++) {
          a = c[y * w + k - 1 - d];
          bb = d < R ? c[y * w + k + d] : 0;
          out[y * nw + nw - 1 - d] = ov(a, bb);
        }
      }
      return { w: nw, h: h, cells: out, ox: b.ox, oy: b.oy, flip: 'R' };
    }
    var T = k, B = h - k;
    if (B >= T) {
      nh = B;
      for (d = 0; d < nh; d++) {
        for (x = 0; x < w; x++) {
          a = c[(k + d) * w + x];
          bb = d < T ? c[(k - 1 - d) * w + x] : 0;
          out[d * w + x] = ov(a, bb);
        }
      }
      return { w: w, h: nh, cells: out, ox: b.ox, oy: b.oy + k, flip: 'T' };
    }
    nh = T;
    for (d = 0; d < nh; d++) {
      for (x = 0; x < w; x++) {
        a = c[(k - 1 - d) * w + x];
        bb = d < B ? c[(k + d) * w + x] : 0;
        out[(nh - 1 - d) * w + x] = ov(a, bb);
      }
    }
    return { w: w, h: nh, cells: out, ox: b.ox, oy: b.oy, flip: 'B' };
  }

  // 折れる線をすべて並べる（縦線が先、横線があと。gen_stages.py の moves と同じ順）
  function moves(b) {
    var out = [], k;
    for (k = 1; k < b.w; k++) out.push(['V', k]);
    for (k = 1; k < b.h; k++) out.push(['H', k]);
    return out;
  }

  function find(b, target) {
    for (var i = 0; i < b.cells.length; i++) if (b.cells[i] === target) return i;
    return -1;
  }

  // 目標ひとつを満たすか。正の数はその値が盤にある、負の数 -c は色 c が盤に1枚もない（消し切り）
  function has(b, t) {
    if (t > 0) return find(b, t) >= 0;
    for (var i = 0; i < b.cells.length; i++) if (b.cells[i] && Math.floor(b.cells[i] / 100) === -t) return false;
    return true;
  }

  // 目標（値の並び）がすべて盤にそろっているか
  function winAll(b, targets) {
    for (var i = 0; i < targets.length; i++) if (!has(b, targets[i])) return false;
    return true;
  }

  // 上限 limit 回までに目標がすべてそろう手順の数（そろった時点で終わり）。確かめ用
  function countSolutions(b, targets, limit) {
    if (limit === 0) return 0;
    var ms = moves(b), n = 0;
    for (var i = 0; i < ms.length; i++) {
      var r = fold(b, ms[i]);
      n += winAll(r, targets) ? 1 : countSolutions(r, targets, limit - 1);
    }
    return n;
  }

  return { ov: ov, fold: fold, moves: moves, find: find, has: has, winAll: winAll, countSolutions: countSolutions };
})();
if (typeof module !== 'undefined') module.exports = FoldCore;
