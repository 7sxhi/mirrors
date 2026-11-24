# 折り紙盤の規則とソルバー（core.js と同じ規則。変えるときは両方を直す）
#
# マスは 色*100+数（色 1=赤 2=青 3=黄）、0 は空き。
# 解析のときだけ、打ち消し（違う色どうしの重なり）を一度でも通ったマスに FLAG を足して印にする。
# 印は遊びの値には影響しない。印のある空きマス（打ち消しで消えた跡）に重なってきたマスも印を受け継ぐ。
# 「打ち消しでしか届かない」盤とは、どの解でも、勝った時点の目標のマスに必ず印がある盤のこと。

FLAG = 1000
COLOR_NAME = {1: '赤', 2: '青', 3: '黄'}


def ov(a, b):
    """2マスの重なり。同じ色は足し算、違う色は大きいほうが差だけ残る（同じ数なら消える）。"""
    f = a >= FLAG or b >= FLAG
    a %= FLAG
    b %= FLAG
    if a == 0 or b == 0:
        r = a or b
    else:
        ca, va = divmod(a, 100)
        cb, vb = divmod(b, 100)
        if ca == cb:
            r = ca * 100 + min(va + vb, 99)
        else:
            f = True
            if va == vb:
                r = 0
            elif va > vb:
                r = ca * 100 + (va - vb)
            else:
                r = cb * 100 + (vb - va)
    return r + FLAG if f else r


def fold(w, h, cells, move):
    """折り線で短い側を長い側へ鏡写しに重ねる。同じ長さなら左を右へ、上を下へ。"""
    t, k = move
    if t == 'V':
        L, R = k, w - k
        if R >= L:
            nw = R
            out = [0] * (nw * h)
            for y in range(h):
                row = y * w
                for d in range(nw):
                    a = cells[row + k + d]
                    b = cells[row + k - 1 - d] if d < L else 0
                    out[y * nw + d] = ov(a, b) if (a or b) else 0
        else:
            nw = L
            out = [0] * (nw * h)
            for y in range(h):
                row = y * w
                for d in range(nw):
                    a = cells[row + k - 1 - d]
                    b = cells[row + k + d] if d < R else 0
                    out[y * nw + nw - 1 - d] = ov(a, b) if (a or b) else 0
        return (nw, h, tuple(out))
    T, B = k, h - k
    if B >= T:
        nh = B
        out = [0] * (w * nh)
        for d in range(nh):
            ra = (k + d) * w
            rb = (k - 1 - d) * w
            for x in range(w):
                a = cells[ra + x]
                b = cells[rb + x] if d < T else 0
                out[d * w + x] = ov(a, b) if (a or b) else 0
    else:
        nh = T
        out = [0] * (w * nh)
        for d in range(nh):
            ra = (k - 1 - d) * w
            rb = (k + d) * w
            for x in range(w):
                a = cells[ra + x]
                b = cells[rb + x] if d < B else 0
                out[(nh - 1 - d) * w + x] = ov(a, b) if (a or b) else 0
    return (w, nh, tuple(out))


def moves(w, h):
    return [('V', k) for k in range(1, w)] + [('H', k) for k in range(1, h)]


def present(cells):
    """盤にある値（印は外す）。"""
    return {c % FLAG for c in cells if c % FLAG}


def present_clean(cells):
    """印のない（打ち消しを通っていない）マスの値。"""
    return {c for c in cells if 0 < c < FLAG}


def hit(pres, t):
    """目標ひとつを満たすか。t > 0 はその値が盤にある、t < 0 は色 -t が盤に1枚もない（消し切り）。"""
    if t > 0:
        return t in pres
    return all(v // 100 != -t for v in pres)


def hit_clean(clean, t):
    # 消し切りは打ち消しなしでは起きない（同じ色は足すだけでマスは減らない）ので、印なしでは満たさない扱い
    return t > 0 and t in clean


def is_win(cells, targets):
    p = present(cells)
    return all(hit(p, t) for t in targets)


def is_win_clean(cells, targets):
    p = present_clean(cells)
    return all(hit_clean(p, t) for t in targets)


def solutions(start, targets, limit):
    """上限 limit 回までに目標がすべてそろう手順（そろった時点で終わり）。
    返り値は (手順, 印なしでそろったか) の並び。"""
    out = []

    def rec(s, left, path):
        if left == 0:
            return
        for m in moves(s[0], s[1]):
            t = fold(*s, m)
            if is_win(t[2], targets):
                out.append((path + [m], is_win_clean(t[2], targets)))
            else:
                rec(t, left - 1, path + [m])

    rec(start, limit, [])
    return out


def p_random(start, targets, limit):
    """毎回でたらめに折り線を選んだとき、上限までに目標がそろう確率。"""
    memo = {}

    def rec(s, left):
        key = (s, left)
        if key in memo:
            return memo[key]
        ms = moves(s[0], s[1])
        if left == 0 or not ms:
            memo[key] = 0.0
            return 0.0
        p = 0.0
        for m in ms:
            t = fold(*s, m)
            p += 1.0 if is_win(t[2], targets) else rec(t, left - 1)
        memo[key] = p / len(ms)
        return memo[key]

    return rec(start, limit)


def replay_wins(start, seq, targets):
    """手順をなぞって、途中か最後に目標がそろうか（そろった時点で止める）。"""
    s = start
    for m in seq:
        if m[0] == 'V' and m[1] >= s[0]:
            return False
        if m[0] == 'H' and m[1] >= s[1]:
            return False
        s = fold(*s, m)
        if is_win(s[2], targets):
            return True
    return False


def swap_stats(start, sols, targets):
    """解の中のとなり合う縦と横の折りを入れ替えた手順が通るか。
    縦と横の折りは紙の形では入れ替えても同じなので、1色・2色では必ず通る。3色だけ重ねる順で結果が変わる。
    返り値は (入れ替えられる組の数, そのうち通らない数)。"""
    tot = fail = 0
    for s in sols:
        for j in range(len(s) - 1):
            if s[j][0] != s[j + 1][0]:
                tot += 1
                s2 = list(s)
                s2[j], s2[j + 1] = s2[j + 1], s2[j]
                if not replay_wins(start, s2, targets):
                    fail += 1
    return tot, fail


def first_depths(start, limit, ntargets, colors_ok=None, vmin=1):
    """各目標の候補（1つならその値、2つなら色の違う2値の組）が初めてそろう折り回数。"""
    first = {}

    def note(cells, d):
        vals = sorted(v for v in present(cells) if v % 100 >= vmin)
        if ntargets == 1:
            for v in vals:
                if v not in first:
                    first[v] = d
        else:
            n = len(vals)
            for i in range(n):
                a = vals[i]
                for j in range(i + 1, n):
                    b = vals[j]
                    if a // 100 == b // 100:
                        continue
                    key = (a, b)
                    if key not in first:
                        first[key] = d

    note(start[2], 0)
    frontier = {start}
    seen = {start}
    for d in range(1, limit + 1):
        nxt = set()
        for s in frontier:
            for m in moves(s[0], s[1]):
                t = fold(*s, m)
                if t in seen:
                    continue
                seen.add(t)
                nxt.add(t)
                note(t[2], d)
        frontier = nxt
    return first


def evaluate_many(start, cands, limit):
    """候補の目標（それぞれ値の組）をまとめて1回の深さ優先でしらべる。
    候補ごとに (届く手順の数, 印なしで届く手順の数, でたらめに折って届く確率, 1手目の正解の数) を返す。"""
    C = len(cands)

    def rec(s, left, active):
        ms = moves(s[0], s[1])
        n = {i: 0 for i in active}
        nc = {i: 0 for i in active}
        p = {i: 0.0 for i in active}
        if not ms:
            return n, nc, p
        for m in ms:
            t = fold(*s, m)
            pres = present(t[2])
            clean = None
            rest = []
            for i in active:
                tg = cands[i]
                if all(hit(pres, x) for x in tg):
                    n[i] += 1
                    p[i] += 1.0
                    if clean is None:
                        clean = present_clean(t[2])
                    if all(hit_clean(clean, x) for x in tg):
                        nc[i] += 1
                else:
                    rest.append(i)
            if rest and left > 1:
                cn, cc, cp = rec(t, left - 1, rest)
                for i in rest:
                    n[i] += cn[i]
                    nc[i] += cc[i]
                    p[i] += cp[i]
        k = len(ms)
        for i in active:
            p[i] /= k
        return n, nc, p

    # 1手目の正解の数も数えるため、根だけ手で回す
    ms = moves(start[0], start[1])
    tot_n = [0] * C
    tot_nc = [0] * C
    tot_p = [0.0] * C
    firsts = [0] * C
    for m in ms:
        t = fold(*start, m)
        pres = present(t[2])
        clean = present_clean(t[2])
        rest = []
        for i in range(C):
            tg = cands[i]
            if all(hit(pres, x) for x in tg):
                tot_n[i] += 1
                tot_p[i] += 1.0
                firsts[i] += 1
                if all(hit_clean(clean, x) for x in tg):
                    tot_nc[i] += 1
            else:
                rest.append(i)
        if rest and limit > 1:
            cn, cc, cp = rec(t, limit - 1, rest)
            for i in rest:
                tot_n[i] += cn[i]
                tot_nc[i] += cc[i]
                tot_p[i] += cp[i]
                if cn[i] > 0:
                    firsts[i] += 1
    k = len(ms)
    return [(tot_n[i], tot_nc[i], tot_p[i] / k, firsts[i]) for i in range(C)]
