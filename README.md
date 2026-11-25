# 折り紙盤

紙を折って、重なったマスを合わせるパズル。

遊ぶ: https://7sxhi.github.io/mirrors/

作: [@7sxhi](https://x.com/7sxhi)

## 遊び方

- 紙の上と左にある丸いつまみが折り線。押すと、短い側が鏡写しに裏返って長い側に重なる。同じ長さなら左が右へ、上が下へ。
- 折り線の名前は、縦の線が左から 1・2・3…、横の線が上から A・B・C…。名前は最初の紙で決まり、折っても変わらない。折った順は「2 → B → 4」のように書く。
- スマホはつまみを1回押すと折ったあとの数が予告され、同じつまみをもう一度押すと折る。マウスはつまみに乗せると予告が出て、押すと折る。
- 重なったマスは、同じ色なら数を足す。違う色なら打ち消し合い、大きいほうが差だけ残る（同じ数なら両方消える）。
- 上限の回数までに目標のマスを作る。目標が2つ以上ある面は、すべてが同時に盤にそろったらクリア。「消」の札は、その色を盤から1枚残らず消す目標。

## 面

| 組 | 中身 |
|---|---|
| 練習 1〜5 | 1色・2色、目標1つ。折る・足す・打ち消す・消し切るを1面ずつ覚える |
| 本編 1〜12 | 3色、色の違う目標2つを同時に。小さい盤から鬼（8x8、上限5回）まで |
| おまけ 1〜6 | 3色。大きい盤・鬼・消し切りの発展を2面ずつ |

面の札:

- 順: どの解も、となり合う縦と横の折りを入れ替えると通らない面。縦と横の折りは紙の形では入れ替えても同じなので、1色・2色では必ず通る（2色の打ち消しは「赤を+、青を-」の足し算と同じ）。3色だけ重ねる順で結果が変わる。
- 打消: どの解でも、目標のマスが打ち消しを通って出来ている面。
- ひび: 別の面（元の盤）と1マスだけ違う盤。目標と上限は同じなのに、元の盤の答えは通らない。

本編とおまけは、どの解も縦と横の両方の折りを使う盤だけにしてある（横だけで届く盤は列ごとに別々に読めて易しすぎるため）。

## ファイル

| ファイル | 中身 |
|---|---|
| index.html | 画面（面選びと遊ぶ画面）。core.js と stages.js を読む |
| core.js | 規則（JS）と、確かめ用の解の数え上げ |
| stages.js | 盤面（生成物。手で直さない） |
| card.png・icon.svg・icon-180.png | Twitter のカードの絵とアイコン（art/ の台から Edge で撮る） |
| fold_rules.py | 規則（Python）、解の列挙、でたらめに折って届く確率、打ち消しの印、縦横の入れ替えの確かめ |
| gen2.py・gen_extra.py | 試作の版（v2a）の盤面を作る |
| gen3.py | 本編の「順」の面を作る |
| gen_bonus.py | おまけ6面を作る |
| build.py | v2a の面と gen3・gen_bonus の面から、練習・本編・おまけに組んで stages.js を書く |
| heat.py | 各面の「1マスの重み」（クリア後の地図）を stages.js に書き足す |
| chaos.py | 色の数とカオスの関係を測る（cands/chaos.txt・chaos_nt2.txt） |
| cands/ | 候補（各枠の上位30）と記録 |
| test/ | 確かめ用の HTML |
| art/ | カードの絵とアイコンを撮る台 |
| v1/・v2a/・v3a/ | 途中の版（v1 は最初の4面、v2a は1色〜3色とおまけの18面、v3a は練習と本編の17面） |

規則は fold_rules.py と core.js の2か所にある。変えるときは両方を直し、下の「確かめ」を通す。

## 盤面の作り直し

```
python gen3.py full 300 8          # 本編の「順」の面（cands/gen3_stages.json）
python gen_bonus.py full 300 8     # おまけ6面（cands/bonus_stages.json）
python build.py                    # 組んで stages.js を書く
python heat.py                     # 1マスの重みを書き足す（いちばん最後）
```

v2a の面そのものを作り直すときは `python gen2.py full 300 8` のあと `python gen_extra.py full 300 8`（stages.js を丸ごと書き直すので、できたものを v2a/stages.js に写す）。
Windows では並列の子が fold_rules.py などを読み直すので、回している間はそれらを編集しない。

## 確かめ

Edge のヘッドレスで test/ の HTML を開く。

```
E="msedge のある場所"
F="--headless=new --disable-gpu --allow-file-access-from-files --user-data-dir=作業用フォルダ"
"$E" $F --virtual-time-budget=120000 --dump-dom file:///…/mirrors/test/check2.html
```

- test/check2.html: 各面で、答えをなぞると最後の手で初めてそろうか、JS で数えた解の数が Python の nsol と同じか、ひびの面の答えが入れ替えると通らないか。最後に ALL OK と出る。
- 画面: `sh test/mk_preview.sh` で写しを作り、`--force-prefers-reduced-motion --screenshot=... --window-size=600,1300` で test/phone.html#sM3（390px の枠）などを撮る。`phone.html?play_answer#sM3` は答えをなぞったあと、`phone.html?play_twin#sM10` はひびの面で元の盤の答えをなぞったあと。
- ヘッドレスは幅が 492 より狭くならないので、電話の幅は phone.html の枠で見る。仮想時間ではアニメが進まないので --force-prefers-reduced-motion を付ける。
