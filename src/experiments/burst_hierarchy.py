"""起爆强度层级，输出到 demo/12_起爆层级/。

文献（牛津语音学）：
    **bursts tend to show a strength hierarchy of
    voiceless aspirated > voiceless unaspirated > voiced**

我们原来 p/t/k 与 b/d/g 用同一个脉冲增益，所以 d/t、b/p 的起爆一样响，
这是它们仍然难分的原因之一。

各声库实测「前 8ms 起爆峰值」的送气−不送气差值：

    Teto日  +4.7 dB
    Teto英  +9.5 dB
    Kumi中  +0.9 dB

差异很大，所以四档给不同的差值，其余全部沿用已定稿的结构（demo/11 的 04）：

    01_无层级   差值 0dB（当前）
    02_差4dB    不送气 = 0.63
    03_差6dB    不送气 = 0.50
    04_差9dB    不送气 = 0.35
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

OUT = os.path.join("demo", "12_起爆层级")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

VARIANTS = {
    "01_无层级": 0.0,
    "02_差4dB": 4.0,
    "03_差6dB": 6.0,
    "04_差9dB": 9.0,
}


def scale_for(diff_db):
    return 10.0 ** (-diff_db / 20.0)


def apply(diff_db):
    s = scale_for(diff_db)
    for k in ("p", "t", "k"):
        ph.CONSONANTS[k]["burst_scale"] = 1.0
    for k in ("b", "d", "g"):
        ph.CONSONANTS[k]["burst_scale"] = s


def restore():
    for k in ph.CONSONANTS:
        ph.CONSONANTS[k].pop("burst_scale", None)


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, diff in VARIANTS.items():
        apply(diff)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for s in SYLS:
            audio, _ = render.render_cv(s[0], s[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{s}.wav"), audio)
        print(f"  {name}: {len(SYLS)} 个音节（不送气 ×{scale_for(diff):.2f}）")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
