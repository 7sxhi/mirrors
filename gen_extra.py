# 折り紙盤 v2 のおまけの面（4組）と、1色の「ひび」のやり直し
#
#   python gen_extra.py calib [秒] [並列数]   おまけの枠を少しだけ回して、候補の数を見る
#   python gen_extra.py full [秒] [並列数]    おまけの枠を回し、stages.js の4組と 1-5 を差し替えて書き戻す
#
# gen2.py full のあとに回す（gen2.py は stages.js を丸ごと書き直すので、おまけが消える）。
# 目標の値は正なら「その値を盤に作る」、負の -c なら「色 c を盤から消し切る」（fold_rules.hit）。
import json
import os
import random
import sys
import multiprocessing as mp

import fold_rules as R
import gen2 as G

HERE = os.path.dirname(os.path.abspath(__file__))

# kind: 'pair' 色の違う2値を同時に / 'clear' 1色を消し切る / 'clearmake' 1色を消し切り、別の色の値を作る
EXTRA = [
    dict(id='4-1', group=4, name='消し切り', kind='clear', colorsets=[[1, 2]], w=6, h=6, dens=0.6, vmax=3,
         nt=1, limit=3, min=3, tmin=1, nsol=(1, 8), p=(0.001, 0.08), pt=0.01, cancel='any'),
    dict(id='4-2', group=4, name='消して作る', kind='clearmake', colorsets=[[1, 2, 3]], w=6, h=6, dens=0.65, vmax=3,
         nt=2, limit=3, min=3, tmin=4, nsol=(1, 6), p=(0.0005, 0.02), pt=0.003, cancel='any'),
    dict(id='4-3', group=4, name='横長', kind='pair', colorsets=[[1, 2, 3]], w=9, h=5, dens=0.6, vmax=3,
         nt=2, limit=4, min=4, tmin=4, nsol=(1, 12), p=(0.0, 0.002), pt=0.0003, cancel='any'),
    dict(id='4-4', group=4, name='鬼', kind='pair', colorsets=[[1, 2, 3]], w=8, h=8, dens=0.6, vmax=3,
         nt=2, limit=5, min=5, tmin=5, nsol=(1, 24), p=(0.0, 0.0002), pt=0.00003, cancel='any'),
]
# 1色のひび: gen2 では 1-4 から作れなかったので、小さい盤を元にして順に試す
TWIN1_BASES = ['1-3', '1-2', '1-1']


def first_depths_ex(start, limit, kind, colors, vmin):
    """消し切りの目標の候補が初めてそろう折り回数。clear は (-c,)、clearmake は (-c, v)。"""
    first = {}

    def note(cells, d):
        pres = R.present(cells)
        for c in colors:
            if any(v // 100 == c for v in pres):
                continue
            if kind == 'clear':
                key = (-c,)
                if key not in first:
                    first[key] = d
            else:
                for v in pres:
                    if v % 100 >= vmin:
                        key = (-c, v)
                        if key not in first:
                            first[key] = d

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


def score_ex(sp, c):
    # 消し切りの目標（負の値）は目標の大きさの点に入れない
    return G.score(sp, dict(c, targets=[t for t in c['targets'] if t > 0]))


def work_ex(args):
    sp, seed, nboards = args
    if sp['kind'] == 'pair':
        return G.work(args)
    rng = random.Random(seed)
    out = []
    for _ in range(nboards):
        b, cs = G.rand_board(rng, sp)
        first = first_depths_ex(b, sp['min'], sp['kind'], cs, sp['tmin'])
        cands = [k for k, d in first.items() if d == sp['min']]
        if not cands:
            continue
        cands.sort(key=lambda t: -sum(x % 100 for x in t if x > 0))
        cands = cands[:24]
        res = R.evaluate_many(b, cands, sp['limit'])
        best = None
        for tg, (n, nc, p, firsts) in zip(cands, res):
            if not G.judge(sp, n, nc, p):
                continue
            c = dict(cells=list(b[2]), w=b[0], h=b[1], targets=list(tg), n=n, nc=nc, p=p, firsts=firsts,
                     colors=cs, seed=seed)
            c['score'] = score_ex(sp, c)
            if best is None or c['score'] < best['score']:
                best = c
        if best:
            out.append(best)
    return out


def count_sols(args):
    st = args
    b = (st['w'], st['h'], tuple(st['cells']))
    return st['id'], len(R.solutions(b, tuple(st['targets']), st['limit'])), st['nsol']


def make_twin(pool, base, sp, nproc, tw_id):
    """gen2.py の main のひびづくりと同じ選び方。見つからなければ None。"""
    b = (base['w'], base['h'], tuple(base['cells']))
    tg = tuple(base['targets'])
    base_sols = R.solutions(b, tg, sp['limit'])
    muts = G.mutations(b, base['colors'], sp['vmax'])
    rnd = random.Random(5)
    rnd.shuffle(muts)
    batches = [muts[i::nproc * 4] for i in range(nproc * 4)]
    res = []
    for r in pool.imap_unordered(G.twin_work, [(b, tg, sp['limit'], [s for s, _ in base_sols], bt) for bt in batches]):
        res.extend(r)
    print('%s（元 %s）のひびの候補 %d' % (tw_id, base['id'], len(res)), flush=True)
    if not res:
        return None
    for r in res:
        b4 = (base['w'], base['h'], tuple(r['cells']))
        r['p'] = R.p_random(b4, tg, sp['limit'])
    same_cancel = lambda r: (r['nclean'] == 0) == base['cancelReq']
    res.sort(key=lambda r: (not r['firstdiff'], not same_cancel(r), len(r['sols']), r['p']))
    best = res[0]
    b4 = (base['w'], base['h'], tuple(best['cells']))
    sols4 = R.solutions(b4, tg, sp['limit'])
    c4 = dict(w=base['w'], h=base['h'], cells=best['cells'], targets=base['targets'], p=best['p'],
              firsts=len({tuple(s[0]) for s, _ in sols4}), colors=base['colors'])
    wipe4 = G.wipe_rate(b4, tg, sols4, base['colors'], sp['vmax'])
    rec = G.stage_record(dict(sp, id=tw_id), c4, sols4, wipe4, 'ひび')
    rec.update(crack=best['cell'], crackFrom=base['cells'][best['cell']], twinOf=base['id'])
    with open(os.path.join(HERE, 'cands', tw_id + '.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(of=base['id'], cands=res[:30]), f, ensure_ascii=False)
    print('%s ひび cell %d %d->%d 解 %d p=%.6f 1手目から違う=%s' % (
        tw_id, best['cell'], base['cells'][best['cell']], best['to'], len(sols4), best['p'], best['firstdiff']),
        flush=True)
    return rec


def load_stages():
    s = open(os.path.join(HERE, 'stages.js'), encoding='utf-8').read()
    return json.loads(s[s.index('['):s.rindex(']') + 1])


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'calib'
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else (20 if mode == 'calib' else 300)
    nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    os.makedirs(os.path.join(HERE, 'cands'), exist_ok=True)
    stages = load_stages()

    # 規則を変えたあとの確かめ: 今の stages.js の解の数が Python でも同じか
    if mode == 'full':
        with mp.Pool(nproc) as pool:
            bad = [r for r in pool.map(count_sols, stages) if r[1] != r[2]]
        print('今の面の解の数の照合: %s' % ('すべて同じ' if not bad else bad), flush=True)
        if bad:
            sys.exit(1)

    chosen = {}
    summary = []
    for k, sp in enumerate(EXTRA):
        found, boards, dt = G.run_spec(sp, budget, 900000 + 100000 * k, nproc, worker=work_ex)
        line = '%s 盤 %d 枚 %.0f 秒 候補 %d' % (sp['id'], boards, dt, len(found))
        if found:
            b = found[0]
            line += ' 一番: 目標 %s n=%d nc=%d p=%.6f 1手目=%d' % (b['targets'], b['n'], b['nc'], b['p'], b['firsts'])
        print(line, flush=True)
        summary.append(line)
        with open(os.path.join(HERE, 'cands', sp['id'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(dict(spec=sp, boards=boards, seconds=dt, cands=found[:30]), f, ensure_ascii=False)
        if found:
            chosen[sp['id']] = found[0]
    if mode == 'calib':
        return

    new = []
    with mp.Pool(nproc) as pool:
        for sp in EXTRA:
            c = chosen.get(sp['id'])
            if not c:
                print('枠 %s は見つからず' % sp['id'], flush=True)
                continue
            b = (c['w'], c['h'], tuple(c['cells']))
            sols = R.solutions(b, tuple(c['targets']), sp['limit'])
            wipe = G.wipe_rate(b, tuple(c['targets']), sols, c['colors'], sp['vmax'])
            new.append(G.stage_record(sp, c, sols, wipe, sp['name']))
            print('%s 1マスで解が全滅する割合 %.3f' % (sp['id'], wipe), flush=True)
        by_id = {s['id']: s for s in stages}
        for bid in TWIN1_BASES:
            base = by_id.get(bid)
            if not base:
                continue
            sp = next(s for s in G.SPECS if s['id'] == bid)
            rec = make_twin(pool, base, sp, nproc, '1-5')
            if rec:
                new.append(rec)
                summary.append('1-5 ひび 元 %s' % bid)
                break

    new_ids = {s['id'] for s in new}
    keep = [s for s in stages if s['group'] != 4 and s['id'] not in new_ids]
    out = sorted(keep + new, key=lambda s: (s['group'], s['id']))
    with open(os.path.join(HERE, 'stages.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('// gen2.py と gen_extra.py が書き出した盤面。手で直さない\n')
        f.write('var STAGES = ' + json.dumps(out, ensure_ascii=False) + ';\n')
    with open(os.path.join(HERE, 'cands', 'summary_extra.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary) + '\n')
    print('書き出し stages.js（%d 面、おまけ・やり直し %d 面）' % (len(out), len(new)), flush=True)


if __name__ == '__main__':
    main()
