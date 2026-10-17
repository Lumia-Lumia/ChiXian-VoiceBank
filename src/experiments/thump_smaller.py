"""d/g 的低频冲击继续往小试，输出到 demo/21_冲击更小/。

上一轮（demo/20）用户判定 **×0.5 是要的**，但想知道更小的冲击怎么样。
这一组固定其他一切（齿龈带通仍是 (3400,9000)、d/g 起爆 −5dB），只动
d/g 的 `thump_scale`：

    01_半      0.50
    02_三成    0.30
    03_一成五  0.15
    04_去掉    0.00

尺度参考：冲击的 RMS 是脉冲的 1.5 倍（THUMP_GAIN=1.5），两者不相关叠加，
所以 1.0→0.5 只降 3.2dB，0.5→0 再降 2.0dB。**四个变体之间不到 2dB**，
听感差别主要在 250Hz 那声「咚」的有无，而不是整体音量。
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

OUT = os.path.join("demo", "21_冲击更小")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

VARIANTS = {
    "01_半":     0.50,
    "02_三成":   0.30,
    "03_一成五": 0.15,
    "04_去掉":   0.00,
}


def apply(scale):
    # 只动 d/g。b 的可听性依赖冲击，p/t/k 用户已认可，都不碰
    for k in ("d", "g"):
        ph.CONSONANTS[k]["burst_scale"] = 0.56
        ph.CONSONANTS[k]["thump_scale"] = scale
    for k in ("p", "t", "k", "b"):
        ph.CONSONANTS[k]["burst_scale"] = 1.0


def restore():
    for k in ph.CONSONANTS:
        ph.CONSONANTS[k].pop("burst_scale", None)
        ph.CONSONANTS[k].pop("thump_scale", None)


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, s in VARIANTS.items():
        apply(s)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for syl in SYLS:
            audio, _ = render.render_cv(syl[0], syl[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{syl}.wav"), audio)
        print(f"  {name}: d/g 冲击 ×{s}")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
