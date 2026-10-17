"""让 b 听得清，输出到 demo/17_b的清晰度/。

问题：`b` 听不清，`p` 没问题。

结构原因：普通话 b 不送气，辅音段只有 26ms（闭合50 + 起爆6 + 送气6 + 过渡14），
其中只有 6ms 起爆是真正可听的。

第一轮结论：
  * **起爆加长到 12ms 是对的**（用户确认），已落地到 b/d/g
  * 双唇带通抬到 (600,1600) **过于明显**，需要小幅调整

所以这一轮固定 b/d/g 起爆 12ms，只把双唇带通分四小步：

    01_原样       (400, 950)
    02_抬一点     (450, 1050)
    03_抬两步     (500, 1200)
    04_抬三步     (550, 1350)

注意双唇带通是 b 与 p 共用的，所以也渲了 pa，确认 p 没有被带坏。
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

OUT = os.path.join("demo", "17_b的清晰度")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

_ORIG = ph.PLACE_BURST["bilabial"]

VARIANTS = {
    "01_原样": (400.0, 950.0),
    "02_抬一点": (450.0, 1050.0),
    "03_抬两步": (500.0, 1200.0),
    "04_抬三步": (550.0, 1350.0),
}


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, band in VARIANTS.items():
        ph.PLACE_BURST["bilabial"] = band
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for s in SYLS:
            audio, _ = render.render_cv(s[0], s[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{s}.wav"), audio)
        print(f"  {name}: 双唇带通 {band}")
    ph.PLACE_BURST["bilabial"] = _ORIG
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
