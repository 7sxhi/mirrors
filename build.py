# 練習（1色・2色）と本編（3色）に組み直して stages.js を書く（11-25 朝のユーザーの方針: 1色・2色はチュートリアル、3色が本編）
#
#   python build.py
#
# 材料は v2a/stages.js（11-25 未明の18面）と cands/gen3_stages.json（gen3.py の順番の面）と
# cands/bonus_stages.json（gen_bonus.py のおまけ6面）。
# 書いたあとに heat.py を回して1マスの重みを足す。
import json
import os

import fold_rules as R
import gen2 as G
import gen3 as N
import gen_extra as X

HERE = os.path.dirname(os.path.abspath(__file__))

# (新しい id, 表示の番号, 組, 材料, 札, 覚えること)  組 1=練習 2=本編前半 3=本編後半 4=おまけ
LAYOUT = [
    ('T1', '1', 1, 'v2a:1-1', '', 'つまみを押すと紙が折れる。重なった同じ色のマスは数を足す。'),
    ('T2', '2', 1, 'v2a:1-2', '', '折る線の位置で重なり方が変わる。3回折って大きな数を作る。'),
    ('T3', '3', 1, 'v2a:2-1', '', '違う色が重なると打ち消し合い、大きいほうが差だけ残る。'),
    ('T4', '4', 1, 'v2a:2-2', '', '打ち消しを使わないと目標に届かない盤。'),
    ('T5', '5', 1, 'v2a:4-1', '消し切り', '打ち消されたマスは消える。青を盤から1枚残らず消す。'),
    ('M1', '1', 2, 'gen3:N4', '', '3色では重ねる順で結果が変わる。同じ2本の線でも、縦→横と横→縦で違う盤になる。ここからは目標2つを同時にそろえる。'),
    ('M2', '2', 2, 'v2a:3-1', '', ''),
    ('M3', '3', 2, 'gen3:N5', '', ''),
    ('M4', '4', 2, 'gen3:N6b', '', ''),  # 11-25 朝まで v2a:3-2。横だけで解けて易しすぎたので差し替え
    ('M5', '5', 2, 'gen3:N6', '', ''),
    ('M6', '6', 2, 'v2a:4-2', '消して作る', '「消」の札は、その色を盤から消し切る目標。'),
    ('M7', '7', 3, 'gen3:N7', '', ''),
    ('M8', '8', 3, 'v2a:4-3', '横長', ''),
    ('M9', '9', 3, 'v2a:3-3', '', ''),
    ('M10', '10', 3, 'v2a:3-5', '', ''),
    ('M11', '11', 3, 'v2a:3-4', '', ''),
    ('M12', '12', 3, 'v2a:4-4', '鬼', '上限5回。'),
    ('X1', '1', 4, 'bonus:B1', '大きい盤', ''),
    ('X2', '2', 4, 'bonus:B2', '大きい盤', ''),
    ('X3', '3', 4, 'bonus:B3', '鬼', '上限5回。'),
    ('X4', '4', 4, 'bonus:B4', '鬼', '上限5回。'),
    ('X5', '5', 4, 'bonus:B5', '二色消し', '「消」が2枚。2色を盤から消し切って、残りの色で目標を作る。'),
    ('X6', '6', 4, 'bonus:B6', '消して二つ', '1色を消し切りながら、残り2色の目標を作る。'),
]


def load_js(path):
    s = open(path, encoding='utf-8').read()
    return json.loads(s[s.index('['):s.rindex(']') + 1])


def vmax_v2a(st):
    sid = st.get('twinOf') or st['id']
    for sp in G.SPECS + X.EXTRA:
        if sp['id'] == sid:
            return sp['vmax']
    raise KeyError(sid)


def main():
    old = {s['id']: s for s in load_js(os.path.join(HERE, 'v2a', 'stages.js'))}
    g3 = {e['spec']['id']: e for e in json.load(open(os.path.join(HERE, 'cands', 'gen3_stages.json'), encoding='utf-8'))}
    bpath = os.path.join(HERE, 'cands', 'bonus_stages.json')
    if os.path.exists(bpath):
        g3.update({e['spec']['id']: e for e in json.load(open(bpath, encoding='utf-8'))})
    old2new = {src.split(':')[1]: nid for nid, _, _, src, _, _ in LAYOUT if src.startswith('v2a:')}
    out = []
    for nid, label, group, src, tag, teach in LAYOUT:
        kind, sid = src.split(':')
        if kind == 'v2a':
            st = dict(old[sid])
            st['vmax'] = vmax_v2a(st)
            if st.get('twinOf'):
                st['twinOf'] = old2new[st['twinOf']]
        else:
            if sid not in g3:
                print('%s の材料 %s がない。飛ばす' % (nid, sid), flush=True)
                continue
            sp, c = g3[sid]['spec'], g3[sid]['cand']
            b = (c['w'], c['h'], tuple(c['cells']))
            sols = R.solutions(b, tuple(c['targets']), sp['limit'])
            wipe = G.wipe_rate(b, tuple(c['targets']), sols, c['colors'], sp['vmax'])
            st = G.stage_record(dict(sp, group=group), c, sols, wipe, G.NAMES.get(c['w'], str(c['w'])))
            st['vmax'] = sp['vmax']
        st.update(id=nid, label=label, group=group, src=src, tag=tag, teach=teach)
        b = (st['w'], st['h'], tuple(st['cells']))
        tg = tuple(st['targets'])
        sols = [s for s, _ in R.solutions(b, tg, st['limit'])]
        tot, fail = R.swap_stats(b, sols, tg)
        st.update(swapTot=tot, swapFail=fail, orderReq=(tot > 0 and fail == tot))
        # 縦か横の片方だけで届く解の数（本編では 0 にしたい）
        st['oneAxis'] = sum(1 for s in sols if len({m[0] for m in s}) < 2)
        if group > 1 and st['oneAxis']:
            print('  注意: %s に片方向だけで届く解が %d 通り' % (nid, st['oneAxis']), flush=True)
        st.pop('heat', None)
        out.append(st)
        print('%s（%s） %dx%d 目標 %s 解 %d 入替 %d/%d 順番必須=%s' % (
            nid, src, st['w'], st['h'], st['targets'], st['nsol'], fail, tot, st['orderReq']), flush=True)
    with open(os.path.join(HERE, 'stages.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('// build.py が組み直した盤面（heat.py が重みを足す）。手で直さない\n')
        f.write('var STAGES = ' + json.dumps(out, ensure_ascii=False) + ';\n')
    print('書き出し stages.js（%d 面）' % len(out), flush=True)


if __name__ == '__main__':
    main()
