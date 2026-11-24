# 各面の「1マスの重み」を stages.js に書き足す（画面のクリア後に出す地図）
#
#   python heat.py
#
# heat[i] = マス i を別の値（空き・各色の 1〜vmax）に変えた盤のうち、元の解がひとつも通らなくなる割合（%）。
# 初めから目標がそろってしまう変え方は数えない（wipe と同じ数え方）。
# gen2.py・gen_extra.py・build.py は stages.js を書き直すので、そのあとにこれを回す。
import json
import os

import fold_rules as R
import gen2 as G
import gen_extra as X

HERE = os.path.dirname(os.path.abspath(__file__))


def vmax_of(st):
    if 'vmax' in st:
        return st['vmax']
    sid = st.get('twinOf') or st['id']
    for sp in G.SPECS + X.EXTRA:
        if sp['id'] == sid:
            return sp['vmax']
    raise KeyError(sid)


def heat_of(st):
    w, h = st['w'], st['h']
    b = (w, h, tuple(st['cells']))
    tg = tuple(st['targets'])
    sols = [s for s, _ in R.solutions(b, tg, st['limit'])]
    vmax = vmax_of(st)
    opts = [0] + [c * 100 + v for c in st['colors'] for v in range(1, vmax + 1)]
    heat = []
    tot_all = dead_all = 0
    for i in range(w * h):
        tot = dead = 0
        for o in opts:
            if o == b[2][i]:
                continue
            cells = list(b[2])
            cells[i] = o
            b2 = (w, h, tuple(cells))
            if R.is_win(b2[2], tg):
                continue
            tot += 1
            if not any(R.replay_wins(b2, s, tg) for s in sols):
                dead += 1
        heat.append(round(100 * dead / tot) if tot else 0)
        tot_all += tot
        dead_all += dead
    return heat, (dead_all / tot_all if tot_all else 0.0)


def main():
    stages = X.load_stages()
    for st in stages:
        heat, wipe = heat_of(st)
        st['heat'] = heat
        hot = sum(1 for x in heat if x > 0)
        print('%s 重みのあるマス %d / %d  全体 %.3f（記録 %.3f）' % (st['id'], hot, len(heat), wipe, st['wipe']), flush=True)
    with open(os.path.join(HERE, 'stages.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('// build.py（または gen2.py・gen_extra.py）が書き出し、heat.py が重みを書き足した盤面。手で直さない\n')
        f.write('var STAGES = ' + json.dumps(stages, ensure_ascii=False) + ';\n')


if __name__ == '__main__':
    main()
