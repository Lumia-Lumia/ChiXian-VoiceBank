"""韵头（介音）的长度，输出到 demo/28_韵头长度/。

demo/25 的用户反馈第 3 条：**wa 的 w 太长了，应该很快结束加入 a**，其他韵头
也有同样问题。当前韵头是 ON_RAMP 30ms + FINALS 里给的 55~60ms，合计约 90ms
的 "w" / "y"。

    01_40ms  02_45ms  03_50ms  04_现状（逐条 55~60ms）

FIN_ON_MS 是**过渡段**时长，前面还有 VOWEL_ON_RAMP（30ms）的静止起音，
所以实际韵头 = 30 + FIN_ON_MS（5ms 档约 35ms，40ms 档约 70ms）。

修掉的 bug：滑音段的目标原先写成了介音自己，原地不动，真正的 u→a 落到
韵腹段上摊满 680ms —— wa / wo 因此听着「过渡一直不结束」。
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as C
import dsp
import phonemes as ph
import render
from _demo import fresh, write

OUT = os.path.join("demo", "28_韵头长度")
F0 = 311.1270

# 韵母 → 文件名（都用零声母拼写）
FINALS = {
    "ua": "wa", "uo": "wo", "uai": "wai", "uei": "wei",
    "iao": "yao", "ie": "ye", "ve": "yue", "ian": "yan",
}

VARIANTS = {
    "01_40ms": 40.0,
    "02_45ms": 45.0,
    "03_50ms": 50.0,
    "04_现状": None,      # FINALS 里逐条给的值，55~60ms
}


def main():
    fresh(OUT)
    orig = ph.FIN_ON_MS
    for name, ms in VARIANTS.items():
        ph.FIN_ON_MS = ms
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for fin, fname in FINALS.items():
            audio, _ = render.render_vowel(fin, F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{fname}.wav"), audio)
        print(f"  {name}: 韵头 {'逐条值' if ms is None else f'{ms:.0f}ms'}")
    ph.FIN_ON_MS = orig
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
