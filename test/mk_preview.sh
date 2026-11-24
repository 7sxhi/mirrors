#!/bin/sh
# index.html から確かめ用の写しを作る（Edge のヘッドレスで開く用。URL の末尾に #sM3 などを付けて面を選ぶ）
# preview.html: そのまま / play_answer.html: 開いたら答えをなぞる（「済」にはしない）
# play_twin.html: 元の盤（本編9）を解いたことにして、ひびの面で「元の盤の答えをなぞる」を押す
cd "$(dirname "$0")"
body() { sed -e 's#src="core.js"#src="../core.js"#' -e 's#src="stages.js"#src="../stages.js"#' -e 's#href="icon.svg"#href="../icon.svg"#' ../index.html; }
body > preview.html
body | sed 's#</body>#<script>setTimeout(function(){FoldDebug.replayAnswer();},300);</script>\n</body>#' > play_answer.html
body | sed -e 's#<script src="../core.js">#<script>try{var c=JSON.parse(localStorage.getItem("fold3-cleared")||"{}");c.M9=true;localStorage.setItem("fold3-cleared",JSON.stringify(c));}catch(e){}</script>\n<script src="../core.js">#' \
  -e 's#</body>#<script>setTimeout(function(){document.getElementById("twin-replay").click();},300);</script>\n</body>#' > play_twin.html
