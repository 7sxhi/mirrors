# 折り紙盤の盤面づくり
# 規則は core.js と同じ（マスは 色*100+数、0 は空き。色 1=赤 2=青 3=黄）。
# ソルバーで「最少の折り回数」「上限までに届く手順の数」「でたらめに折って届く確率」を測り、
# 難易度ごとに条件に合う盤を選んで stages.js に書き出す。
import json
import random
import sys
import time


def ov(a, b):
    """2マスの重なり。同じ色は足し算、違う色は大きいほうが差だけ残る（同じ数なら消える）。"""
    if a == 0:
        return b
    if b == 0:
        return a
    ca, va = divmod(a, 100)
    cb, vb = divmod(b, 100)
    if ca == cb:
        return ca * 100 + min(va + vb, 99)
    if va == vb:
        return 0
    return ca * 100 + (va - vb) if va > vb else cb * 100 + (vb - va)


def fold(w, h, cells, move):
    """折り線で短い側を長い側へ鏡写しに重ねる。同じ長さなら左を右へ、上を下へ。"""
    t, k = move
    if t == 'V':
        L, R = k, w - k
        if R >= L:
            nw = R
            out = [0] * (nw * h)
            for y in range(h):
                for d in range(nw):
                    a = cells[y * w + k + d]
                    b = cells[y * w + k - 1 - d] if d < L else 0
                    out[y * nw + d] = ov(a, b)
        else:
            nw = L
            out = [0] * (nw * h)
            for y in range(h):
                for d in range(nw):
                    a = cells[y * w + k - 1 - d]
                    b = cells[y * w + k + d] if d < R else 0
                    out[y * nw + nw - 1 - d] = ov(a, b)
        return (nw, h, tuple(out))
    T, B = k, h - k
    if B >= T:
        nh = B
        out = [0] * (w * nh)
        for d in range(nh):
            for x in range(w):
                a = cells[(k + d) * w + x]
                b = cells[(k - 1 - d) * w + x] if d < T else 0
                out[d * w + x] = ov(a, b)
    else:
        nh = T
        out = [0] * (w * nh)
        for d in range(nh):
            for x in range(w):
                a = cells[(k - 1 - d) * w + x]
                b = cells[(k + d) * w + x] if d < B else 0
                out[(nh - 1 - d) * w + x] = ov(a, b)
    return (w, nh, tuple(out))


def moves(w, h):
    return [('V', k) for k in range(1, w)] + [('H', k) for k in range(1, h)]


def first_depths(start, D):
    """各タイルが初めて盤に出る折り回数（D 回まで）。"""
    first = {}
    for c in start[2]:
        if c:
            first.setdefault(c, 0)
    frontier = {start}
    seen = {start}
    for d in range(1, D + 1):
        nxt = set()
        for s in frontier:
            for m in moves(s[0], s[1]):
                t = fold(*s, m)
                if t in seen:
                    continue
                seen.add(t)
                nxt.add(t)
                for c in t[2]:
                    if c and c not in first:
                        first[c] = d
        frontier = nxt
    return first


def solutions(start, target, limit):
    """上限 limit 回までに目標が出る手順（出た時点で終わり）をすべて返す。"""
    out = []

    def rec(s, left, path):
        if left == 0:
            return
        for m in moves(s[0], s[1]):
            t = fold(*s, m)
            if target in t[2]:
                out.append(path + [m])
            else:
                rec(t, left - 1, path + [m])

    rec(start, limit, [])
    return out


def p_random(start, target, limit):
    """毎回でたらめに折り線を選んだとき、上限までに目標に届く確率。"""
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
            p += 1.0 if target in t[2] else rec(t, left - 1)
        memo[key] = p / len(ms)
        return memo[key]

    return rec(start, limit)


def rand_board(rng, w, h, dens, vmax):
    cells = []
    for _ in range(w * h):
        if rng.random() < dens:
            cells.append(rng.randint(1, 3) * 100 + rng.randint(1, vmax))
        else:
            cells.append(0)
    return (w, h, tuple(cells))


def find_stage(rng, spec, budget):
    t0 = time.time()
    tries = 0
    while time.time() - t0 < budget:
        tries += 1
        b = rand_board(rng, spec['w'], spec['h'], spec['dens'], spec['vmax'])
        first = first_depths(b, spec['min'])
        cands = sorted([c for c, d in first.items() if d == spec['min']], key=lambda c: -(c % 100))
        for tgt in cands[:6]:
            if tgt % 100 < spec['tmin']:
                continue
            sols = solutions(b, tgt, spec['limit'])
            if not (spec['nmin'] <= len(sols) <= spec['nmax']):
                continue
            p = p_random(b, tgt, spec['limit'])
            if not (spec['pmin'] <= p <= spec['pmax']):
                continue
            return b, tgt, sols, p, tries
    return None


def mutate_stage(rng, b3, tgt, sols3, limit, budget):
    """盤3の1マスだけ変えて、同じ目標・同じ上限なのに盤3の解がひとつも通らない盤を探す。"""
    w, h, cells = b3
    set3 = {tuple(s) for s in sols3}
    first3 = {s[0] for s in sols3}
    t0 = time.time()
    opts = [0] + [c * 100 + v for c in (1, 2, 3) for v in (1, 2, 3)]
    best = None
    while time.time() - t0 < budget:
        i = rng.randrange(w * h)
        nv = rng.choice([o for o in opts if o != cells[i]])
        nc = list(cells)
        nc[i] = nv
        b4 = (w, h, tuple(nc))
        if tgt in b4[2]:
            continue
        sols4 = solutions(b4, tgt, limit)
        if not sols4 or len(sols4) > 3:
            continue
        if any(len(s) < limit for s in sols4):
            continue
        if {tuple(s) for s in sols4} & set3:
            continue
        # 盤3の解を盤4でなぞっても届かないことは上の条件で保証される。1手目まで違うものを優先
        score = 1 if not ({s[0] for s in sols4} & first3) else 0
        if best is None or score > best[0]:
            best = (score, b4, i, sols4)
            if score == 1:
                break
    return best


def to_js(b, tgt, sols, p, limit, mn, extra):
    w, h, cells = b
    d = {
        'w': w, 'h': h, 'cells': list(cells), 'target': tgt, 'limit': limit, 'min': mn,
        'nsol': len(sols), 'prand': round(p, 4),
        'answer': [[m[0], m[1]] for m in min(sols, key=len)],
    }
    d.update(extra)
    return d


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    rng = random.Random(seed)
    specs = [
        dict(name='はじめの一枚', w=4, h=4, dens=0.6, vmax=2, min=2, limit=3, tmin=3,
             nmin=4, nmax=60, pmin=0.25, pmax=0.6),
        dict(name='六つ切り', w=6, h=6, dens=0.6, vmax=3, min=3, limit=3, tmin=4,
             nmin=2, nmax=12, pmin=0.01, pmax=0.08),
        dict(name='八つ切り', w=8, h=8, dens=0.6, vmax=3, min=4, limit=4, tmin=5,
             nmin=1, nmax=3, pmin=0.0, pmax=0.01),
    ]
    stages = []
    found3 = None
    for sp in specs:
        r = find_stage(rng, sp, budget=150)
        if r is None:
            print('見つからず', sp['name'], flush=True)
            sys.exit(1)
        b, tgt, sols, p, tries = r
        print(sp['name'], 'tries', tries, 'target', tgt, 'nsol', len(sols), 'p', round(p, 4),
              'answer', sols[0], flush=True)
        stages.append(to_js(b, tgt, sols, p, sp['limit'], sp['min'], {'name': sp['name']}))
        found3 = (b, tgt, sols, sp['limit'])
    b3, tgt, sols3, limit = found3
    m = mutate_stage(rng, b3, tgt, sols3, limit, budget=200)
    if m is None:
        print('ひびの盤が見つからず', flush=True)
    else:
        score, b4, i, sols4 = m
        p4 = p_random(b4, tgt, limit)
        print('ひび', 'cell', i, b3[2][i], '->', b4[2][i], 'nsol', len(sols4), 'p', round(p4, 4),
              'first-move-differs', score, 'answer', sols4[0], flush=True)
        stages.append(to_js(b4, tgt, sols4, p4, limit, limit,
                            {'name': 'ひび', 'crack': i, 'crackFrom': b3[2][i], 'twinOf': 2}))
    with open('stages.js', 'w', encoding='utf-8', newline='\n') as f:
        f.write('// gen_stages.py が書き出した盤面（seed %d）。手で直さない\n' % seed)
        f.write('var STAGES = ' + json.dumps(stages, ensure_ascii=False) + ';\n')
    print('書き出し stages.js', flush=True)


if __name__ == '__main__':
    main()
