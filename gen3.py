# 折り紙盤 v3 の本編（3色）に足す「順番の面」を作る
#
#   python gen3.py calib [秒] [並列数]   各枠を少しだけ回して、候補の数を見る
#   python gen3.py full [秒] [並列数] [枠,枠]  各枠を回し、一番よい盤を cands/gen3_stages.json に書く
#                                            （枠を指定したときは、その枠だけ差し替える）
#
# 「順番の面」: どの解でも、となり合う縦と横の折りを入れ替えると通らなくなる盤（fold_rules.swap_stats）。
# 縦と横の折りは紙の形では入れ替えても同じなので、これは3色の重ねる順だけで起きる。
# order: 'req' 順番の面に限る / 'any' 問わない。mixed: True ならどの解も縦と横の両方を使う
# （横だけで届くと列ごとに別々に読めて易しすぎる。11-25 朝のユーザーの指摘: 旧本編4 は左の2列だけで解けた）。
# 盤面の組み立ては build.py（v2a の面と合わせて stages.js を書く）。
import json
import os
import random
import sys

import fold_rules as R
import gen2 as G

HERE = os.path.dirname(os.path.abspath(__file__))

C3 = [[1, 2, 3]]
SPECS3 = [
    dict(id='N4', colorsets=C3, w=4, h=4, dens=0.8, vmax=3, nt=2, limit=2, min=2, tmin=3,
         nsol=(1, 4), p=(0.02, 0.3), pt=0.08, cancel='any', mixed=True),
    dict(id='N5', colorsets=C3, w=5, h=5, dens=0.7, vmax=3, nt=2, limit=3, min=3, tmin=4,
         nsol=(1, 6), p=(0.003, 0.05), pt=0.01, cancel='any'),
    dict(id='N6', colorsets=C3, w=6, h=6, dens=0.65, vmax=3, nt=2, limit=3, min=3, tmin=5,
         nsol=(1, 4), p=(0.0005, 0.01), pt=0.002, cancel='req'),
    dict(id='N7', colorsets=C3, w=7, h=7, dens=0.6, vmax=3, nt=2, limit=4, min=4, tmin=5,
         nsol=(1, 8), p=(0.0, 0.002), pt=0.0004, cancel='any'),
    dict(id='N6b', colorsets=C3, w=6, h=6, dens=0.65, vmax=3, nt=2, limit=3, min=3, tmin=5,
         nsol=(1, 4), p=(0.001, 0.01), pt=0.004, cancel='any', order='any', mixed=True),
]


def order_ok(b, tg, sp):
    sols = [s for s, _ in R.solutions(b, tg, sp['limit'])]
    if sp.get('mixed') and any(len({m[0] for m in s}) < 2 for s in sols):
        return False, 0
    tot, fail = R.swap_stats(b, sols, tg)
    if sp.get('order', 'req') == 'req':
        return tot > 0 and fail == tot, tot
    return True, tot


def work3(args):
    sp, seed, nboards = args
    rng = random.Random(seed)
    out = []
    for _ in range(nboards):
        b, cs = G.rand_board(rng, sp)
        first = R.first_depths(b, sp['min'], sp['nt'], vmin=sp['tmin'])
        cands = [k for k, d in first.items() if d == sp['min'] and isinstance(k, tuple)]
        if not cands:
            continue
        cands.sort(key=lambda t: -sum(x % 100 for x in t))
        cands = cands[:24]
        res = R.evaluate_many(b, cands, sp['limit'])
        ok = []
        for tg, (n, nc, p, firsts) in zip(cands, res):
            if not G.judge(sp, n, nc, p):
                continue
            c = dict(cells=list(b[2]), w=b[0], h=b[1], targets=list(tg), n=n, nc=nc, p=p, firsts=firsts,
                     colors=cs, seed=seed)
            c['score'] = G.score(sp, c)
            ok.append(c)
        ok.sort(key=lambda c: c['score'])
        # 解をすべて並べて入れ替えを試すのは重いので、点のよい順に3つまで
        for c in ok[:3]:
            good, tot = order_ok(b, tuple(c['targets']), sp)
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
    os.makedirs(os.path.join(HERE, 'cands'), exist_ok=True)
    chosen = []
    for k, sp in enumerate(SPECS3):
        if only and sp['id'] not in only:
            continue
        found, boards, dt = G.run_spec(sp, budget, 3000000 + 100000 * k, nproc, worker=work3)
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
    path = os.path.join(HERE, 'cands', 'gen3_stages.json')
    if only and os.path.exists(path):
        # 指定した枠だけ差し替え、ほかの枠は前の結果を残す
        prev = json.load(open(path, encoding='utf-8'))
        new_ids = {e['spec']['id'] for e in chosen}
        chosen = [e for e in prev if e['spec']['id'] not in new_ids] + chosen
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(chosen, f, ensure_ascii=False)
    print('書き出し cands/gen3_stages.json（%d 枠）' % len(chosen), flush=True)


if __name__ == '__main__':
    main()
