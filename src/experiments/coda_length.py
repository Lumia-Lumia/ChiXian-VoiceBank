"""鼻尾长度，输出到 demo/31_鼻尾长度/。

demo/29 的用户反馈：**yun 的 n 不明显**。

原因不是鼻尾本身 —— 实测 yun 的尾部频谱与 an 的尾部几乎一致（800-1400
−21.7、1400-2200 −23.7）。问题是**前面的 ü 本来就没有中高频**，所以
「变成鼻音」这件事缺少对比；鼻尾只是太短、来不及被听清。

四档只改 CODA_MS：

    01_80ms   现状
    02_110ms
    03_140ms
    04_170ms

这一档同时作用于所有带鼻尾的韵母，所以 an / ang / yin / ying / en 一起渲，
确认加长不会让它们变得拖沓。
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

OUT = os.path.join("demo", "31_鼻尾长度")
F0 = 311.1270

FINALS = {
    "an": "an", "ang": "ang", "en": "en",
    "in": "yin", "ing": "ying", "iong": "yong", "vn": "yun",
}

VARIANTS = {
    "01_80ms": 80.0,
    "02_110ms": 110.0,
    "03_140ms": 140.0,
    "04_170ms": 170.0,
}


def main():
    fresh(OUT)
    orig = ph.CODA_MS
    for name, ms in VARIANTS.items():
        ph.CODA_MS = ms
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for fin, fname in FINALS.items():
            audio, _ = render.render_vowel(fin, F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{fname}.wav"), audio)
        print(f"  {name}: CODA_MS = {ms:.0f}")
    ph.CODA_MS = orig
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
