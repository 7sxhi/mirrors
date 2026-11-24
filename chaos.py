# 色の数とカオスの関係を、盤の大きさと目標の数をそろえて測る（報告用）
#
#   python chaos.py [1色あたりの盤の数] [並列数] [目標の数]
#
# 目標の数を 2 にすると、色の違う2値を同時に（1色は組めないので2色と3色だけ）。記録は chaos_nt2.txt。
#
# A. 縦と横の折りの順を入れ替えたとき、盤が変わる割合
#    1色は足し算、2色は「赤を+、青を-」の足し算と同じなので、順を入れ替えても同じ盤になるはず。
#    3色は重ねる順で結果が変わる（赤3+青1 → 赤2、そこへ黄2 → 消える / 青1+黄2 → 黄1、そこへ赤3 → 赤2）。
# B. 1マスだけ変えたとき、答えがどれだけ動くか（6x6、上限3、目標1つで色の数だけ変える）
#    全滅: 元の解がひとつも通らない / 入れ替わり: 解の集まりが少しでも変わる / 1手目: 正解の1手目の集まりが変わる
#    変え方は「1枚取り除く」（色の数によらない）と「何にでも変える」の2通り。
# C. 3回折ったときに出来る盤の種類の数（手順の数で割る）
import json
import multiprocessing as mp
import os
import random
import sys
import time

import fold_rules as R

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 6
DENS = 0.6
VMAX = 3
LIMIT = 3
VMIN = 4


def rand_board(rng, k):
    cs = [1, 2, 3][:k]
    while True:
        cells = [rng.choice(cs) * 100 + rng.randint(1, VMAX) if rng.random() < DENS else 0 for _ in range(W * H)]
        if all(sum(1 for c in cells if c // 100 == col) >= 2 for col in cs):
            return (W, H, tuple(cells)), cs


def strip(s):
    return (s[0], s[1], tuple(c % R.FLAG for c in s[2]))


def swap_rate(b):
    """縦 a と横 c の組すべてで、縦→横と横→縦の盤が違う割合。"""
    tot = diff = 0
    for a in range(1, b[0]):
        for c in range(1, b[1]):
            x = strip(R.fold(*R.fold(*b, ('V', a)), ('H', c)))
            y = strip(R.fold(*R.fold(*b, ('H', c)), ('V', a)))
            tot += 1
            diff += x != y
    return diff / tot


def diversity(b, depth):
    """depth 回折って出来る盤の種類の数 / 手順の数。"""
    seqs = 0
    states = set()

    def rec(s, d):
        nonlocal seqs
        if d == 0:
            seqs += 1
            states.add(strip(s))
            return
        for m in R.moves(s[0], s[1]):
            rec(R.fold(*s, m), d - 1)

    rec(b, depth)
    return len(states) / seqs


def solset(b, tg):
    return {tuple(tuple(m) for m in s) for s, _ in R.solutions(b, tg, LIMIT)}


def puzzle(rng, k, nt):
    """gen2 と同じ考え方で、3回で初めて出来る値（の組）を目標にし、解が 1〜12 通りの盤を作る。"""
    while True:
        b, cs = rand_board(rng, k)
        first = R.first_depths(b, LIMIT, nt, vmin=VMIN)
        cands = [v if isinstance(v, tuple) else (v,) for v, d in first.items() if d == LIMIT]
        if not cands:
            continue
        rng.shuffle(cands)
        res = R.evaluate_many(b, cands[:12], LIMIT)
        ok = [tg for tg, r in zip(cands[:12], res) if 1 <= r[0] <= 12]
        if ok:
            return b, cs, ok[0]


def measure(args):
    k, seed, nt = args
    rng = random.Random(seed)
    b, cs, tg = puzzle(rng, k, nt)
    base = solset(b, tg)
    first0 = {s[0] for s in base}
    opts = [0] + [c * 100 + v for c in cs for v in range(1, VMAX + 1)]
    out = {'k': k, 'nsol': len(base), 'swap': swap_rate(b), 'div': diversity(b, 3)}
    for kind in ('remove', 'any'):
        tot = wipe = change = firstch = 0
        for i in range(W * H):
            if kind == 'remove':
                tos = [0] if b[2][i] else []
            else:
                tos = [o for o in opts if o != b[2][i]]
            for o in tos:
                cells = list(b[2])
                cells[i] = o
                b2 = (W, H, tuple(cells))
                if R.is_win(b2[2], tg):
                    continue
                tot += 1
                if not any(R.replay_wins(b2, list(s), tg) for s in base):
                    wipe += 1
                s2 = solset(b2, tg)
                if s2 != base:
                    change += 1
                if {s[0] for s in s2} != first0:
                    firstch += 1
        out[kind] = (wipe / tot, change / tot, firstch / tot) if tot else (0.0, 0.0, 0.0)
    return out


def main():
    nb = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    nt = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    ks = (1, 2, 3) if nt == 1 else (2, 3)
    t0 = time.time()
    jobs = [(k, 7000000 + 10000 * k + i, nt) for k in ks for i in range(nb)]
    with mp.Pool(nproc) as pool:
        res = pool.map(measure, jobs, chunksize=2)
    lines = ['色の数とカオス（6x6、上限3、目標%dつ、各 %d 盤、%.0f 秒）' % (nt, nb, time.time() - t0), '']
    lines.append('色  解の数  縦横入替で変わる  3回で出来る盤の種類/手順  '
                 '取り除き: 全滅 入替 1手目  何にでも: 全滅 入替 1手目')
    summary = {}
    for k in ks:
        rs = [r for r in res if r['k'] == k]
        mean = lambda f: sum(f(r) for r in rs) / len(rs)
        row = dict(nsol=mean(lambda r: r['nsol']), swap=mean(lambda r: r['swap']), div=mean(lambda r: r['div']),
                   rm=[mean(lambda r, j=j: r['remove'][j]) for j in range(3)],
                   any=[mean(lambda r, j=j: r['any'][j]) for j in range(3)])
        summary[k] = row
        lines.append('%d   %5.2f   %6.1f%%            %6.3f                     %5.1f%% %5.1f%% %5.1f%%    %5.1f%% %5.1f%% %5.1f%%' % (
            k, row['nsol'], 100 * row['swap'], row['div'],
            100 * row['rm'][0], 100 * row['rm'][1], 100 * row['rm'][2],
            100 * row['any'][0], 100 * row['any'][1], 100 * row['any'][2]))
    txt = '\n'.join(lines) + '\n'
    print(txt, flush=True)
    tag = '' if nt == 1 else '_nt%d' % nt
    with open(os.path.join(HERE, 'cands', 'chaos%s.txt' % tag), 'w', encoding='utf-8') as f:
        f.write(txt)
    with open(os.path.join(HERE, 'cands', 'chaos%s.json' % tag), 'w', encoding='utf-8') as f:
        json.dump(dict(summary=summary, raw=res), f, ensure_ascii=False)


if __name__ == '__main__':
    main()
