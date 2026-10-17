"""d 的起爆段时长，输出到 demo/24_d起爆时长/。

上一轮（demo/23）选定齿龈带通 (3400,8500)，冲击沿用 d=0.3 / g=0.5。

用户要求缩短 d 的起爆段（当前 6ms）。注意起爆段同时也是低频冲击的渲染窗口
（`out[a:b] += th`），所以缩短它会把冲击一起截短 —— 这是同一个旋钮，不是
额外变量。

    01_6ms   现状
    02_5ms
    03_4ms
    04_3ms

只动 d。g 保持 6ms，ba/pa/ta/ka 完全不变，可作参照。
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

OUT = os.path.join("demo", "24_d起爆时长")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]
ALV = (3400.0, 8500.0)

_ORIG = ph.PLACE_BURST["alveolar"]

VARIANTS = {
    "01_6ms": 6,
    "02_5ms": 5,
    "03_4ms": 4,
    "04_3ms": 3,
}


def apply(burst_ms):
    ph.PLACE_BURST["alveolar"] = ALV
    ph.CONSONANTS["d"]["burst"] = burst_ms
    ph.CONSONANTS["g"]["burst"] = 6
    for k, t in {"d": 0.3, "g": 0.5}.items():
        ph.CONSONANTS[k]["burst_scale"] = 0.56
        ph.CONSONANTS[k]["thump_scale"] = t
    for k in ("p", "t", "k", "b"):
        ph.CONSONANTS[k]["burst_scale"] = 1.0


def restore():
    ph.PLACE_BURST["alveolar"] = _ORIG
    ph.CONSONANTS["d"]["burst"] = 6
    for k in ph.CONSONANTS:
        ph.CONSONANTS[k].pop("burst_scale", None)
        ph.CONSONANTS[k].pop("thump_scale", None)


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, ms in VARIANTS.items():
        apply(ms)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for syl in SYLS:
            audio, _ = render.render_cv(syl[0], syl[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{syl}.wav"), audio)
        print(f"  {name}: d 起爆 {ms}ms")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
