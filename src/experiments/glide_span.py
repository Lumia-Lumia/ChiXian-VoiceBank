"""韵尾滑音占韵腹的比例，输出到 demo/27_滑音占比/。

demo/26 结论：**亮鼻尾是对的**，已设为 render.CODA_F / CODA_BW 的默认值。
剩下的问题是滑音占韵腹多大比例 —— 用户听完 100% 与 60% 两端后要中间值。

    01_100   整段都在走
    02_87
    03_73
    04_60    前 40% 保持韵腹

只渲 a / ai / ao / an / ang；a 是纯单元音，四档应当完全一致。
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

OUT = os.path.join("demo", "27_滑音占比")
F0 = 311.1270
FINALS = ["a", "ai", "ao", "an", "ang"]

VARIANTS = {
    "01_100": 1.00,
    "02_87": 0.87,
    "03_73": 0.73,
    "04_60": 0.60,
}


def main():
    fresh(OUT)
    orig = ph.FIN_GLIDE_SPAN
    for name, span in VARIANTS.items():
        ph.FIN_GLIDE_SPAN = span
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for fin in FINALS:
            audio, _ = render.render_vowel(fin, F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{fin}.wav"), audio)
        print(f"  {name}: 滑音占韵腹 {span:.0%}")
    ph.FIN_GLIDE_SPAN = orig
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
