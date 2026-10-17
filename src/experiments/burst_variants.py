"""起爆音色四档对比，输出到 demo/06_爆破_部位带通/。

测量结论：我们的起爆在 4kHz 以上比参考低 30~40dB ——

              2-4k    4-8k   8-16k   质心
    Teto ta  -11.7    -8.8   -12.5   2029Hz
    我们 ta   -6.1   -42.7   -74.3   1123Hz

根因是起爆走了两条路，两条都不给高频：
  * 经声道的那一份过 5 级串联谐振器，5kHz 以上是 60dB/oct 陡降
  * 部位带通那一份只到 3.2kHz，而且电平只有 -24dB

所以四档都在动**部位带通**：放宽上限、提高电平，并决定要不要撤掉
经声道那一路的 2.7kHz 低通。

    B1_现状      基线
    B2_带通到7k  齿龈 (2000,7000) 软腭 (1000,5000) 双唇 (300,1500)，增益 0.20
    B3_带通更响  同上，增益 0.35
    B4_去低通    B2 基础上把经声道那一路的 BURST_LP 从 2700 提到 20000
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

OUT = os.path.join("demo", "06_爆破_部位带通")
F0 = 311.1270
SYLS = ["ba", "pa", "da", "ta", "ga", "ka"]

_ORIG_BAND = dict(ph.PLACE_BURST)
_ORIG_GB = ph.GAIN_BURST
_ORIG_LP = ph.BURST_LP

WIDE = {"bilabial": (300.0, 1500.0),
        "alveolar": (2000.0, 7000.0),
        "velar": (1000.0, 5000.0)}

VARIANTS = {
    "01_现状": dict(),
    "02_带通到7k": dict(band=WIDE, gain=0.20),
    "03_带通更响": dict(band=WIDE, gain=0.35),
    "04_去低通": dict(band=WIDE, gain=0.20, lp=20000.0),
}


def restore():
    ph.PLACE_BURST.clear()
    ph.PLACE_BURST.update(_ORIG_BAND)
    ph.GAIN_BURST = _ORIG_GB
    ph.BURST_LP = _ORIG_LP


def apply(p):
    restore()
    if "band" in p:
        ph.PLACE_BURST.update(p["band"])
    if "gain" in p:
        ph.GAIN_BURST = p["gain"]
    if "lp" in p:
        ph.BURST_LP = p["lp"]


def main():
    fresh(OUT)          # 先清空，免得上一轮的变体残留
    for name, params in VARIANTS.items():
        apply(params)
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        for s in SYLS:
            audio, _ = render.render_cv(s[0], s[1], F0)
            audio = dsp.normalize(audio, dsp.rms(audio),
                                  C.VOICED_RMS_DBFS, C.PEAK_CEILING)
            write(os.path.join(d, f"{s}.wav"), audio)
        print(f"  {name}: {len(SYLS)} 个音节")
    restore()
    print(f"输出目录：{OUT}")


if __name__ == "__main__":
    main()
