"""辅音段总电平四档，输出到 demo/15_辅音电平/。

用户反馈爆破整体偏轻。`GAIN_RELEASE` 是释放段（起爆噪声 + 送气）的总增益，
直接决定整个辅音段有多响；脉冲和部位带通另有各自的增益，不受影响。

测量对照（辅音段 RMS，相对元音电平）：

    Teto日  pa -10.8  ta -20.0  ka  -9.2
    Kumi中  pa -16.3  ta -16.9  ka -15.4
    Eme俄   pa  -8.6  ta -10.2  ka  -9.7
    我们    pa -11.6  ta -13.4  ka -11.4

按这个指标我们已经在参考区间内，但听感说轻，所以四档往上推：

    01_现状  0.32（当前）
    02_加3dB 0.45
    03_加6dB 0.64
    04_加9dB 0.90
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

OUT = os.path.join("demo", "15_辅音电平")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

_ORIG = ph.GAIN_RELEASE

VARIANTS = {
    "01_现状": 0.32,
    "02_加3dB": 0.45,
    "03_加6dB": 0.64,
    "04_加9dB": 0.90,
}


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, g in VARIANTS.items():
        ph.GAIN_RELEASE = g
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for s in SYLS:
            audio, _ = render.render_cv(s[0], s[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{s}.wav"), audio)
        print(f"  {name}: GAIN_RELEASE {g}（{20*np.log10(g/0.32):+.1f}dB）")
    ph.GAIN_RELEASE = _ORIG
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
