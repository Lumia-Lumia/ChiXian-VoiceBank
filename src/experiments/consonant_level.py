"""辅音段整体电平四档，输出到 demo/16_辅音总电平/。

用户反馈爆破整体偏轻。查下来，单独调任何一个成分都改不动整体：

    固定窗口 [60,106]ms 内，关掉各成分后辅音能量的变化
        起爆脉冲    -1.4 dB
        低频冲击    -0.9 dB
        部位带通    -0.2 dB
        送气        -0.1 dB

送气几乎不贡献能量（46ms 里电平本就低），`GAIN_RELEASE` 单独提 9dB 也只换来
1dB 的实际变化。所以要整体提响必须四个成分一起缩放 —— `CONSONANT_GAIN`。

第一轮（1.00 / 1.41 / 2.00 / 2.82）的结论是 **2.00 已经明显偏响**，
所以在 1.41 附近细分，步长约 1dB：

    01_115   ×1.15  +1.2dB
    02_130   ×1.30  +2.3dB
    03_145   ×1.45  +3.2dB
    04_160   ×1.60  +4.1dB
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

OUT = os.path.join("demo", "16_辅音总电平")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

_ORIG = ph.CONSONANT_GAIN

VARIANTS = {
    "01_115": 1.15,
    "02_130": 1.30,
    "03_145": 1.45,
    "04_160": 1.60,
}


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, g in VARIANTS.items():
        ph.CONSONANT_GAIN = g
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for s in SYLS:
            audio, _ = render.render_cv(s[0], s[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{s}.wav"), audio)
        print(f"  {name}: 总增益 {g}（{20*np.log10(g):+.1f}dB）")
    ph.CONSONANT_GAIN = _ORIG
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
