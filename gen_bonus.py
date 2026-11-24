# 折り紙盤 完成版の「おまけ」6面（大きい盤・鬼級・消し切りの発展を2面ずつ）を作る
#
#   python gen_bonus.py calib [秒] [並列数]
#   python gen_bonus.py full [秒] [並列数] [枠,枠]   一番よい盤を cands/bonus_stages.json に書く（枠指定時はその枠だけ差し替え）
#
# どの面も3色で、どの解も縦と横の両方を使う（mixed）。order='req' はどの解も縦横の入れ替えで通らない「順」の面。
# kind: 'pair' 色の違う2値を同時に / 'clear2make' 2色を消し切って残りの色の値を作る / 'clearpair' 1色を消し切って残り2色の値を作る
import json
import os
import random
import sys

import fold_rules as R
import gen2 as G

HERE = os.path.dirname(os.path.abspath(__file__))
C3 = [[1, 2, 3]]

SPECS_B = [
    dict(id='B1', name='大9', kind='pair', colorsets=C3, w=9, h=9, dens=0.55, vmax=3, nt=2, limit=4, min=4, tmin=5,
         nsol=(1, 8), p=(0.0, 0.001), pt=0.0003, cancel='any', order='any'),
    dict(id='B2', name='大10', kind='pair', colorsets=C3, w=10, h=7, dens=0.55, vmax=3, nt=2, limit=4, min=4, tmin=5,
         nsol=(1, 8), p=(0.0, 0.001), pt=0.0002, cancel='any', order='req'),
    dict(id='B3', name='鬼', kind='pair', colorsets=C3, w=7, h=7, dens=0.6, vmax=3, nt=2, limit=5, min=5, tmin=5,
         nsol=(1, 12), p=(0.0, 0.0002), pt=0.00003, cancel='any', order='req'),
    dict(id='B4', name='鬼', kind='pair', colorsets=C3, w=8, h=8, dens=0.6, vmax=3, nt=2, limit=5, min=5, tmin=6,
         nsol=(1, 12), p=(0.0, 0.0001), pt=0.00002, cancel='any', order='req'),
    dict(id='B5', name='二色消し', kind='clear2make', colorsets=C3, w=6, h=6, dens=0.55, vmax=3, nt=3, limit=3, min=3,
         tmin=4, nsol=(1, 6), p=(0.0002, 0.02), pt=0.002, cancel='any', order='any'),
    dict(id='B6', name='消して二つ', kind='clearpair', colorsets=C3, w=7, h=7, dens=0.6, vmax=3, nt=3, limit=4, min=4,
         tmin=4, nsol=(1, 8), p=(0.0, 0.002), pt=0.0003, cancel='any', order='any'),
]


def first_depths_b(start, limit, kind, vmin):
    """消し切りの発展の目標の候補が初めてそろう折り回数。"""
    first = {}

    def note(cells, d):
        pres = R.present(cells)
        absent = [c for c in (1, 2, 3) if not any(v // 100 == c for v in pres)]
        keys = []
        if kind == 'clear2make' and len(absent) >= 2:
            for i in range(len(absent)):
                for j in range(i + 1, len(absent)):
                    rest = [c for c in (1, 2, 3) if c not in (absent[i], absent[j])][0]
                    for v in pres:
                        if v // 100 == rest and v % 100 >= vmin:
                            keys.append((-absent[i], -absent[j], v))
        elif kind == 'clearpair':
            for c in absent:
                vs = sorted(v for v in pres if v % 100 >= vmin)
                for i in range(len(vs)):
                    for j in range(i + 1, len(vs)):
                        if vs[i] // 100 != vs[j] // 100:
                            keys.append((-c, vs[i], vs[j]))
        for k in keys:
            if k not in first:
                first[k] = d

    note(start[2], 0)
    frontier = {start}
    seen = {start}
    for d in range(1, limit + 1):
        nxt = set()
        for s in frontier:
            for m in R.moves(s[0], s[1]):
                t = R.fold(*s, m)
                if t in seen:
                    continue
                seen.add(t)
                nxt.add(t)
                note(t[2], d)
        frontier = nxt
    return first


def check(b, tg, sp):
    """どの解も縦横の両方を使うか、順の面の条件を満たすか。返り値は (よいか, 入れ替えの組の数)。"""
    sols = [s for s, _ in R.solutions(b, tg, sp['limit'])]
    if any(len({m[0] for m in s}) < 2 for s in sols):
        return False, 0
    tot, fail = R.swap_stats(b, sols, tg)
    if sp['order'] == 'req':
        return tot > 0 and fail == tot, tot
    return True, tot


def work_b(args):
    sp, seed, nboards = args
    rng = random.Random(seed)
    out = []
    for _ in range(nboards):
        b, cs = G.rand_board(rng, sp)
        if sp['kind'] == 'pair':
            first = R.first_depths(b, sp['min'], 2, vmin=sp['tmin'])
            cands = [k for k, d in first.items() if d == sp['min'] and isinstance(k, tuple)]
        else:
            first = first_depths_b(b, sp['min'], sp['kind'], sp['tmin'])
            cands = [k for k, d in first.items() if d == sp['min']]
        if not cands:
            continue
        cands.sort(key=lambda t: -sum(x % 100 for x in t if x > 0))
        cands = cands[:24]
        res = R.evaluate_many(b, cands, sp['limit'])
        ok = []
        for tg, (n, nc, p, firsts) in zip(cands, res):
            if not G.judge(sp, n, nc, p):
                continue
            c = dict(cells=list(b[2]), w=b[0], h=b[1], targets=list(tg), n=n, nc=nc, p=p, firsts=firsts,
                     colors=cs, seed=seed)
            c['score'] = G.score(sp, dict(c, targets=[t for t in tg if t > 0]))
            ok.append(c)
        ok.sort(key=lambda c: c['score'])
        for c in ok[:3]:
            good, tot = check(b, tuple(c['targets']), sp)
            if good:
                c['swaps'] = tot
                out.append(c)
                break
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'calib'
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else (20 if mode == 'calib' else 300)
    nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    only = sys.argv[4].split(',') if len(sys.argv) > 4 else None
    chosen = []
    for k, sp in enumerate(SPECS_B):
        if only and sp['id'] not in only:
            continue
        found, boards, dt = G.run_spec(sp, budget, 5000000 + 100000 * k, nproc, worker=work_b)
        line = '%s 盤 %d 枚 %.0f 秒 候補 %d' % (sp['id'], boards, dt, len(found))
        if found:
            b = found[0]
            line += ' 一番: 目標 %s n=%d nc=%d p=%.6f 1手目=%d 入替 %d' % (
                b['targets'], b['n'], b['nc'], b['p'], b['firsts'], b['swaps'])
        print(line, flush=True)
        with open(os.path.join(HERE, 'cands', sp['id'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(dict(spec=sp, boards=boards, seconds=dt, cands=found[:30]), f, ensure_ascii=False)
        if found:
            chosen.append(dict(spec=sp, cand=found[0]))
    if mode == 'calib':
        return
    path = os.path.join(HERE, 'cands', 'bonus_stages.json')
    if only and os.path.exists(path):
        prev = json.load(open(path, encoding='utf-8'))
        new_ids = {e['spec']['id'] for e in chosen}
        chosen = [e for e in prev if e['spec']['id'] not in new_ids] + chosen
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(chosen, f, ensure_ascii=False)
    print('書き出し cands/bonus_stages.json（%d 枠）' % len(chosen), flush=True)


if __name__ == '__main__':
    main()
