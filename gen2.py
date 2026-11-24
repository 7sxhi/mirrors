# 折り紙盤 v2 の盤面づくり
#
#   python gen2.py calib [秒]          各枠を少しだけ回して、候補がどれくらい出るかを見る
#   python gen2.py full [秒] [並列数]   各枠を回して一番よい盤を選び、stages.js と cands/*.json を書く
#
# 枠（SPECS）は色の数で3つの組に分ける。1色と2色は目標1つ、3色は色の違う目標2つを同時にそろえる。
# 「打ち消し必須」の枠は、どの解でも目標のマスが打ち消しを通って出来ている盤だけを採る（fold_rules.py の印）。
import json
import math
import multiprocessing as mp
import os
import random
import sys
import time

import fold_rules as R

HERE = os.path.dirname(os.path.abspath(__file__))

# group: 色の数 / nt: 目標の数 / limit: 折れる上限 / min: 目標が初めてそろう折り回数
# tmin: 目標の数の下限 / nsol: 上限までに届く手順の数の範囲 / p: でたらめに折って届く確率の範囲
# pt: 選ぶときに近づける確率 / cancel: 'req' 打ち消し必須、'no' 打ち消しなしの解がある、'any' どちらでも
SPECS = [
    dict(id='1-1', group=1, colorsets=[[3]], w=4, h=4, dens=0.7, vmax=2, nt=1, limit=2, min=2, tmin=4,
         nsol=(2, 10), p=(0.12, 0.6), pt=0.3, cancel='any'),
    dict(id='1-2', group=1, colorsets=[[1]], w=5, h=5, dens=0.6, vmax=3, nt=1, limit=3, min=3, tmin=6,
         nsol=(1, 10), p=(0.02, 0.2), pt=0.06, cancel='any'),
    dict(id='1-3', group=1, colorsets=[[2]], w=6, h=6, dens=0.6, vmax=3, nt=1, limit=3, min=3, tmin=8,
         nsol=(1, 4), p=(0.002, 0.03), pt=0.01, cancel='any'),
    dict(id='1-4', group=1, colorsets=[[3]], w=8, h=8, dens=0.55, vmax=3, nt=1, limit=4, min=4, tmin=10,
         nsol=(1, 12), p=(0.0, 0.002), pt=0.0005, cancel='any'),
    dict(id='2-1', group=2, colorsets=[[1, 2]], w=4, h=4, dens=0.75, vmax=3, nt=1, limit=3, min=2, tmin=3,
         nsol=(3, 20), p=(0.08, 0.4), pt=0.2, cancel='any'),
    dict(id='2-2', group=2, colorsets=[[2, 3]], w=5, h=5, dens=0.65, vmax=3, nt=1, limit=3, min=3, tmin=3,
         nsol=(1, 8), p=(0.005, 0.08), pt=0.02, cancel='req'),
    dict(id='2-3', group=2, colorsets=[[1, 3]], w=6, h=6, dens=0.6, vmax=3, nt=1, limit=3, min=3, tmin=5,
         nsol=(1, 6), p=(0.003, 0.04), pt=0.01, cancel='no'),
    dict(id='2-4', group=2, colorsets=[[1, 2]], w=8, h=8, dens=0.6, vmax=3, nt=1, limit=4, min=4, tmin=5,
         nsol=(1, 12), p=(0.0, 0.002), pt=0.0003, cancel='req'),
    dict(id='3-1', group=3, colorsets=[[1, 2, 3]], w=5, h=5, dens=0.7, vmax=3, nt=2, limit=3, min=3, tmin=3,
         nsol=(1, 10), p=(0.004, 0.08), pt=0.02, cancel='any'),
    dict(id='3-2', group=3, colorsets=[[1, 2, 3]], w=6, h=6, dens=0.65, vmax=3, nt=2, limit=3, min=3, tmin=4,
         nsol=(1, 4), p=(0.0005, 0.01), pt=0.003, cancel='no'),
    dict(id='3-3', group=3, colorsets=[[1, 2, 3]], w=8, h=8, dens=0.6, vmax=3, nt=2, limit=4, min=4, tmin=4,
         nsol=(1, 12), p=(0.0, 0.001), pt=0.0002, cancel='no'),
    dict(id='3-4', group=3, colorsets=[[1, 2, 3]], w=8, h=8, dens=0.6, vmax=3, nt=2, limit=4, min=4, tmin=3,
         nsol=(1, 3), p=(0.0, 0.001), pt=0.0002, cancel='req'),
]
# 「ひび」の枠: 元の盤の1マスだけ変えて、同じ目標・同じ上限なのに元の解がひとつも通らない盤
TWINS = [dict(id='1-5', of='1-4'), dict(id='2-5', of='2-4'), dict(id='3-5', of='3-3')]


def rand_board(rng, sp):
    cs = rng.choice(sp['colorsets'])
    while True:
        cells = []
        for _ in range(sp['w'] * sp['h']):
            if rng.random() < sp['dens']:
                cells.append(rng.choice(cs) * 100 + rng.randint(1, sp['vmax']))
            else:
                cells.append(0)
        if all(sum(1 for c in cells if c // 100 == col) >= 2 for col in cs):
            return (sp['w'], sp['h'], tuple(cells)), cs


def judge(sp, n, nc, p):
    if not (sp['nsol'][0] <= n <= sp['nsol'][1]):
        return False
    if not (sp['p'][0] <= p <= sp['p'][1]):
        return False
    if sp['cancel'] == 'req' and nc != 0:
        return False
    if sp['cancel'] == 'no' and nc == 0:
        return False
    return True


def score(sp, c):
    # 小さいほどよい。確率を pt に近づけ、解は少なめ、目標の数は大きめ、1手目の正解は少なめ
    lp = math.log10(max(c['p'], 1e-7))
    s = abs(lp - math.log10(sp['pt']))
    s += 0.08 * c['n']
    s += 0.1 * c['firsts']
    s -= 0.02 * sum(t % 100 for t in c['targets'])
    return s


def work(args):
    sp, seed, nboards = args
    rng = random.Random(seed)
    out = []
    for _ in range(nboards):
        b, cs = rand_board(rng, sp)
        first = R.first_depths(b, sp['min'], sp['nt'], vmin=sp['tmin'])
        cands = [k if isinstance(k, tuple) else (k,) for k, d in first.items() if d == sp['min']]
        if not cands:
            continue
        cands.sort(key=lambda t: -sum(x % 100 for x in t))
        cands = cands[:24]
        res = R.evaluate_many(b, cands, sp['limit'])
        best = None
        for tg, (n, nc, p, firsts) in zip(cands, res):
            if not judge(sp, n, nc, p):
                continue
            c = dict(cells=list(b[2]), w=b[0], h=b[1], targets=list(tg), n=n, nc=nc, p=p, firsts=firsts,
                     colors=cs, seed=seed)
            c['score'] = score(sp, c)
            if best is None or c['score'] < best['score']:
                best = c
        if best:
            out.append(best)
    return out


def run_spec(sp, budget, seed0, nproc, worker=None):
    """枠ひとつを budget 秒だけ回す。仕事は同時に nproc*2 個まで出し、時間が来たら残りは捨てる。"""
    t0 = time.time()
    found = []
    boards = 0
    per = 4 if sp['w'] * sp['h'] >= 64 else 12
    seed = seed0
    with mp.Pool(nproc) as pool:
        pend = []
        while True:
            while len(pend) < nproc * 2 and time.time() - t0 < budget:
                pend.append(pool.apply_async(worker or work, ((sp, seed, per),)))
                seed += 1
            if not pend:
                break
            r = pend.pop(0).get()
            boards += per
            found.extend(r)
            if time.time() - t0 > budget:
                break
    found.sort(key=lambda c: c['score'])
    return found, boards, time.time() - t0


def mutations(b, colors, vmax):
    w, h, cells = b
    opts = [0] + [c * 100 + v for c in colors for v in range(1, vmax + 1)]
    out = []
    for i in range(w * h):
        for o in opts:
            if o != cells[i]:
                nc = list(cells)
                nc[i] = o
                out.append((i, o, (w, h, tuple(nc))))
    return out


def wipe_rate(b, targets, sols, colors, vmax):
    """1マスだけ変えた盤のうち、元の解がひとつも通らなくなる割合（初めから目標がある盤は数えない）。"""
    tot = 0
    dead = 0
    for i, o, b2 in mutations(b, colors, vmax):
        if R.is_win(b2[2], targets):
            continue
        tot += 1
        if not any(R.replay_wins(b2, s, targets) for s, _ in sols):
            dead += 1
    return dead / tot if tot else 0.0


def twin_work(args):
    base, targets, limit, base_sols, batch = args
    base_set = {tuple(map(tuple, s)) for s in base_sols}
    base_first = {tuple(s[0]) for s in base_sols}
    out = []
    for i, o, b4 in batch:
        if R.is_win(b4[2], targets):
            continue
        sols = R.solutions(b4, targets, limit)
        if not sols or len(sols) > 12:
            continue
        if any(len(s) < limit for s, _ in sols):
            continue
        seqs = [tuple(tuple(m) for m in s) for s, _ in sols]
        if set(seqs) & base_set:
            continue
        if any(R.replay_wins(base, list(s), targets) for s in seqs):
            continue
        firstdiff = not ({s[0] for s in seqs} & base_first)
        nc = sum(1 for _, c in sols if c)
        out.append(dict(cell=i, to=o, cells=list(b4[2]), sols=[[list(m) for m in s] for s in seqs], nclean=nc,
                        firstdiff=firstdiff))
    return out


def stage_record(sp, c, sols, wipe, name):
    clean_ok = [s for s, cl in sols if cl]
    ans = min((s for s, _ in sols), key=len)
    return dict(id=sp['id'], group=sp['group'], name=name, w=c['w'], h=c['h'], cells=c['cells'],
                targets=c['targets'], limit=sp['limit'], min=sp['min'], nsol=len(sols), nclean=len(clean_ok),
                prand=round(c['p'], 6), firsts=c['firsts'], cancelReq=(len(clean_ok) == 0 and sp['group'] > 1),
                wipe=round(wipe, 3), answer=[list(m) for m in ans], colors=c['colors'])


NAMES = {4: '豆', 5: '小', 6: '中', 8: '大'}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'calib'
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else (20 if mode == 'calib' else 240)
    nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    only = sys.argv[4].split(',') if len(sys.argv) > 4 else None
    os.makedirs(os.path.join(HERE, 'cands'), exist_ok=True)
    chosen = {}
    summary = []
    for k, sp in enumerate(SPECS):
        if only and sp['id'] not in only:
            continue
        found, boards, dt = run_spec(sp, budget, 100000 * (k + 1), nproc)
        line = '%s 盤 %d 枚 %.0f 秒 候補 %d' % (sp['id'], boards, dt, len(found))
        if found:
            b = found[0]
            line += ' 一番: 目標 %s n=%d nc=%d p=%.5f 1手目=%d' % (
                b['targets'], b['n'], b['nc'], b['p'], b['firsts'])
        print(line, flush=True)
        summary.append(line)
        with open(os.path.join(HERE, 'cands', sp['id'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(dict(spec=sp, boards=boards, seconds=dt, cands=found[:30]), f, ensure_ascii=False)
        if found:
            chosen[sp['id']] = found[0]
    if mode == 'calib':
        return
    with mp.Pool(nproc) as pool:
        stages = []
        for sp in SPECS:
            c = chosen.get(sp['id'])
            if not c:
                print('枠 %s は見つからず' % sp['id'], flush=True)
                continue
            b = (c['w'], c['h'], tuple(c['cells']))
            sols = R.solutions(b, tuple(c['targets']), sp['limit'])
            wipe = wipe_rate(b, tuple(c['targets']), sols, c['colors'], sp['vmax'])
            name = NAMES.get(c['w'], str(c['w']))
            stages.append(stage_record(sp, c, sols, wipe, name))
            print('%s 1マスで解が全滅する割合 %.3f' % (sp['id'], wipe), flush=True)
        by_id = {s['id']: s for s in stages}
        for tw in TWINS:
            base = by_id.get(tw['of'])
            if not base:
                continue
            sp = next(s for s in SPECS if s['id'] == tw['of'])
            b = (base['w'], base['h'], tuple(base['cells']))
            tg = tuple(base['targets'])
            base_sols = R.solutions(b, tg, sp['limit'])
            muts = mutations(b, base['colors'], sp['vmax'])
            rnd = random.Random(5)
            rnd.shuffle(muts)
            batches = [muts[i::nproc * 4] for i in range(nproc * 4)]
            res = []
            for r in pool.imap_unordered(twin_work, [(b, tg, sp['limit'], [s for s, _ in base_sols], bt) for bt in batches]):
                res.extend(r)
            print('%s のひびの候補 %d' % (tw['id'], len(res)), flush=True)
            if not res:
                continue
            for r in res:
                b4 = (base['w'], base['h'], tuple(r['cells']))
                r['p'] = R.p_random(b4, tg, sp['limit'])
            # 1手目まで違うもの、打ち消しの性質が元と同じもの、でたらめに届きにくいものを優先
            same_cancel = lambda r: (r['nclean'] == 0) == base['cancelReq']
            res.sort(key=lambda r: (not r['firstdiff'], not same_cancel(r), len(r['sols']), r['p']))
            best = res[0]
            b4 = (base['w'], base['h'], tuple(best['cells']))
            sols4 = R.solutions(b4, tg, sp['limit'])
            c4 = dict(w=base['w'], h=base['h'], cells=best['cells'], targets=base['targets'], p=best['p'],
                      firsts=len({tuple(s[0]) for s, _ in sols4}), colors=base['colors'])
            wipe4 = wipe_rate(b4, tg, sols4, base['colors'], sp['vmax'])
            rec = stage_record(dict(sp, id=tw['id']), c4, sols4, wipe4, 'ひび')
            rec.update(crack=best['cell'], crackFrom=base['cells'][best['cell']], twinOf=tw['of'])
            stages.append(rec)
            with open(os.path.join(HERE, 'cands', tw['id'] + '.json'), 'w', encoding='utf-8') as f:
                json.dump(dict(of=tw['of'], cands=res[:30]), f, ensure_ascii=False)
            print('%s ひび cell %d %d->%d 解 %d p=%.6f 1手目から違う=%s' % (
                tw['id'], best['cell'], base['cells'][best['cell']], best['to'], len(sols4), best['p'],
                best['firstdiff']), flush=True)
    with open(os.path.join(HERE, 'stages.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('// gen2.py が書き出した盤面。手で直さない\n')
        f.write('var STAGES = ' + json.dumps(stages, ensure_ascii=False) + ';\n')
    with open(os.path.join(HERE, 'cands', 'summary.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary) + '\n')
    print('書き出し stages.js（%d 面）' % len(stages), flush=True)


if __name__ == '__main__':
    main()
